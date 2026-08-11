"""Q29 — the additive-kernel BO arm. Post-hoc model development, labelled as such.

Pre-registered in `docs/OPEN-QUESTIONS.md` Q29, committed before this ran. Check
this file's first output line against that entry's commit timestamp.

**THIS DOES NOT CHANGE E2.** It adds arms. Every comparator is read from
`results/e2-grid.json` exactly as stored, and the run refuses to report anything
until it has regenerated the stored qLogEI arm and found it identical — a new
arm compared against a drifted comparator is not a comparison.

------------------------------------------------------------------------------
THE CONFLICT OF INTEREST, RESTATED WHERE IT WILL BE READ
------------------------------------------------------------------------------

`e2.yaml` registers `no_per_method_tuning: true`. BO is currently losing to
current practice at both dimensions (Q27). This arm was therefore built by
someone who already knew BO was behind, and no result it produces can be a
pre-registered one. The label travels with the number, into the write-up.

What makes it defensible rather than merely declared: the change was chosen
from measurements that already existed (Q22's 93% additivity, Q25's 16% shape
skill), three rival explanations had already been tested and eliminated (Q25
prior, Q21 solver, Q26 opening size), and the model was selected on held-out
FIT before any regret was computed.

What is NOT defensible and is stated in Q29's limitations: nobody has tried to
improve the DoE arm, so this is a tuned method against untuned baselines --
exactly the objection the pre-registration exists to prevent. It is reported,
not managed away.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boec.campaign import Campaign, CampaignConfig      # noqa: E402
from boec.diagnostics import instance_bootstrap         # noqa: E402
from boec.optimizers import AcqConfig                   # noqa: E402
from boec.oracles import load_ensemble                  # noqa: E402
from boec.torch_oracle import BiphasicOracle            # noqa: E402
from run_e2 import (                                    # noqa: E402
    BUDGET, N_INSTANCES, N_SEEDS, SIGMAS, scored_curve, unit_bounds,
)

GRID = Path("results/e2-grid.json")
DOE_D8 = Path("results/e2-doe-d8.json")
OUT = Path("results/q29-additive.json")

DIM = 6
#: Fixed before the run: the head of the ensemble's fixed order, both seeds.
FIDELITY_SUBSAMPLE = 5

ARMS = {
    "qlogei-add": "additive+interaction",
    "qlogei-addonly": "additive",
}


def stored_rows(dim: int) -> dict:
    rows = json.loads(GRID.read_text())
    out = {(r["instance"], r["sigma"], r["seed"], r["arm"]): r
           for r in rows if r["dim"] == dim}
    if dim == 8 and DOE_D8.exists():
        for r in json.loads(DOE_D8.read_text()):
            out[(r["instance"], r["sigma"], r["seed"], "doe")] = r
    return out


def campaign_best(inst, sigma, seed, structure) -> float:
    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cfg = CampaignConfig(d=DIM, budget=BUDGET, q=4, seed=seed,
                         acq=AcqConfig(kind="qlogei"),
                         kernel_structure=structure)
    c = Campaign(o, unit_bounds(DIM), cfg)
    c.run()
    return float(scored_curve(o, c.train_X, c.train_Y)[-1])


def check_fidelity(ens, stored) -> None:
    """The stored qLogEI arm is the comparator. It must still regenerate."""
    worst, n = 0.0, 0
    for sigma in SIGMAS:
        for inst in ens[:FIDELITY_SUBSAMPLE]:
            for seed in range(N_SEEDS):
                got = campaign_best(inst, sigma, seed, "product")
                key = (inst.instance_id, sigma, seed, "qlogei")
                worst = max(worst, abs(got - stored[key]["best"]))
                n += 1
    print(f"  stored qLogEI regenerates: {n} campaigns "
          f"({FIDELITY_SUBSAMPLE} instances), max |delta| = {worst:.3e}")
    if worst > 1e-9:
        print("\nFIDELITY FAILED — the comparator moved. Nothing written.")
        raise SystemExit(1)


def main() -> None:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"Q29 · additive-kernel BO · POST-HOC model development · HEAD={head}")
    print(f"d={DIM}, budget {BUDGET}, {N_INSTANCES} instances x {N_SEEDS} seeds, "
          f"arms: {', '.join(ARMS)}\n")

    ens = load_ensemble(dim=DIM)[:N_INSTANCES]
    stored = stored_rows(DIM)

    print("FIDELITY — the comparator this arm is measured against:")
    check_fidelity(ens, stored)

    print("\nRUNNING:")
    rows = []
    for arm, structure in ARMS.items():
        for sigma in SIGMAS:
            for inst in ens:
                for seed in range(N_SEEDS):
                    best = campaign_best(inst, sigma, seed, structure)
                    rows.append(dict(instance=inst.instance_id, dim=DIM,
                                     sigma=sigma, seed=seed, arm=arm,
                                     kernel_structure=structure, best=best,
                                     regret=float(inst.optimum_value - best)))
            print(f"  {arm} sigma={sigma} done ({len(rows)} rows)", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1))
    report(rows, stored)
    print(f"\nrows written to {OUT}")


def per_instance(rows, sigma, arm, insts) -> np.ndarray:
    """One number per instance, averaged over seeds. Effective n = 25, not 50."""
    return np.array([np.mean([r["regret"] for r in rows
                              if r["sigma"] == sigma and r["arm"] == arm
                              and r["instance"] == i]) for i in insts])


def report(rows, stored) -> None:
    comparators = ["qlogei", "doe", "qlognei", "lhs", "sobol", "random", "coord"]
    for sigma in SIGMAS:
        insts = sorted({r["instance"] for r in rows if r["sigma"] == sigma})
        tag = " <-- where the mechanism predicts the effect" if sigma == 0.10 \
            else " <-- E2 primary cell; no improvement predicted"
        print(f"\n{'=' * 84}\nQ29 · d={DIM} · sigma_rel={sigma} · "
              f"{len(insts)} instances x {N_SEEDS} seeds{tag}\n{'=' * 84}")

        per = {a: per_instance(rows, sigma, a, insts) for a in ARMS}
        for a in comparators:
            vals = [np.mean([stored[(i, sigma, s, a)]["regret"]
                             for s in range(N_SEEDS)]) for i in insts
                    if (i, sigma, 0, a) in stored]
            if len(vals) == len(insts):
                per[a] = np.array(vals)

        print(f"{'arm':>16} {'mean regret':>12} {'median':>9}")
        for a in list(ARMS) + [c for c in comparators if c in per]:
            mark = "  <-- new" if a in ARMS else ""
            print(f"{a:>16} {per[a].mean():>12.4f} {np.median(per[a]):>9.4f}{mark}")

        print(f"\n  paired on instance, new arm minus comparator "
              f"(negative = new arm has LESS regret), n={len(insts)}:")
        for a in ARMS:
            for c in [x for x in comparators if x in per]:
                d = per[a] - per[c]
                m, lo, hi = instance_bootstrap(d, n_boot=2000)
                try:
                    p = wilcoxon(d).pvalue
                except ValueError:
                    p = float("nan")
                star = ""
                if a == "qlogei-add" and c == "qlogei":
                    star = "  <-- THE Q29 PRIMARY"
                elif a == "qlogei-add" and c == "doe":
                    star = "  <-- vs current practice"
                print(f"    {a:>14} vs {c:>8}: {m:>+8.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]  p={p:.4f}{star}")


if __name__ == "__main__":
    main()
