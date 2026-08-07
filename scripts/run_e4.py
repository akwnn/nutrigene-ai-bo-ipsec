"""Run Experiment 4 across Person A's ensemble and report every headline number.

    python scripts/run_e4.py                 # pre-registered: 10 instances, d=6
    python scripts/run_e4.py --instances 40  # scaled — see NOTE below

NOTE ON CHANGING --instances
    The instance count is pre-registered (configs/experiment/e4.yaml). Raising it
    after seeing a result that missed significance, and then reporting the new
    result as though the sample size had been chosen in advance, is exactly the
    practice that makes a finding unpublishable.

    If it is raised: bump ``preregistration_version`` to 2 and state the reason
    in the paper — "the first run at the pre-registered n was underpowered for
    the paired comparison; n was raised on a power calculation performed on that
    run". That is defensible. A silent rerun is not.

Results: results/E4-FIRST-RESULTS.md
"""

from __future__ import annotations

import argparse
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import time
import warnings

import numpy as np
import torch

torch.set_num_threads(1)
warnings.filterwarnings("ignore")

from boec.e4 import E4Config, run_e4_cell, summarise
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

KAPPAS = (0.6, 0.7, 0.8, 0.9)
RULE = "=" * 72


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=6, help="E4 is d=6 only; see spec §6")
    ap.add_argument("--instances", type=int, default=10, help="PRE-REGISTERED at 10")
    ap.add_argument("--kappas", type=float, nargs="+", default=list(KAPPAS))
    args = ap.parse_args()

    if args.instances != 10:
        print(
            f"\n!!! --instances={args.instances} deviates from the pre-registered 10.\n"
            "!!! Bump preregistration_version and state the reason. See this file's docstring.\n"
        )

    instances = load_ensemble(args.dim)[: args.instances]
    print(f"{len(instances)} instances at d={args.dim}, kappa in {args.kappas}")

    t0 = time.perf_counter()
    results = []
    for kappa in args.kappas:
        for i, inst in enumerate(instances):
            results.append(
                run_e4_cell(
                    BiphasicOracle(inst),
                    E4Config(kappa=kappa, seed=i),
                    instance_id=inst.instance_id[:8],
                )
            )
        print(f"  kappa={kappa} done ({time.perf_counter() - t0:.0f}s)")
    print(f"\n{len(results)} cells in {time.perf_counter() - t0:.0f}s\n")

    valid = [r for r in results if r.is_valid]

    print(RULE, "\nVALIDITY — was there anything to extrapolate towards?\n", RULE, sep="")
    print(f"  invalid (true optimum inside the training corner): {len(results) - len(valid)}/{len(results)}")

    print("\n" + RULE, "\nHEADROOM — could the comparison show anything? (< 0.95)\n", RULE, sep="")
    for k in args.kappas:
        sub = [r for r in valid if r.kappa == k]
        if not sub:
            continue
        hs = [r.discrimination.agreement.max_offdiagonal for r in sub]
        n_flat = sum(1 for r in sub if not r.discrimination.agreement.has_headroom)
        print(f"  kappa={k}: median {np.median(hs):.3f}  no-headroom {n_flat}/{len(sub)}")

    print("\n" + RULE, "\nOVER-PREDICTION — the mechanism (response max ~1.0)\n", RULE, sep="")
    for k in args.kappas:
        sub = [r for r in valid if r.kappa == k]
        if not sub:
            continue
        for m in ("second_order", "gp"):
            v = [r.over_prediction[m] for r in sub if np.isfinite(r.over_prediction[m])]
            esc = sum(1 for r in sub if not r.argmax_inside_subbox.get(m, False))
            print(f"  kappa={k} {m:<14} median {np.median(v):+8.3f}  escaped {esc}/{len(sub)}")

    print("\n" + RULE, "\nDISCRIMINATION — the pre-registered primary\n", RULE, sep="")
    for k in args.kappas:
        sub = [r for r in valid if r.kappa == k]
        if not sub:
            continue
        s = summarise(sub)
        gp, nn = s["spearman_gp"], s["spearman_nearest_neighbour"]
        d, lo, hi, sig = s["gp_beats_null_paired"]
        print(f"  kappa={k}: GP rho {gp[0]:+.3f} | nearest-neighbour rho {nn[0]:+.3f}")
        print(f"           PAIRED difference {d:+.4f} [{lo:+.4f}, {hi:+.4f}]  significant={sig}")

    print("\n" + RULE, "\nPOOLED\n", RULE, sep="")
    s = summarise(valid)
    print(f"  cells                {s['n_cells']}/{s['n_cells_total']}")
    print(f"  over-prediction      {s['over_prediction_mean']:+.3f} "
          f"[{s['over_prediction_ci'][0]:+.3f}, {s['over_prediction_ci'][1]:+.3f}]")
    print(f"  fraction extrapolated {s['fraction_extrapolated']:.2f}")
    print(f"  stationary kinds     {s['stationary_kinds']}")
    print(f"  parametric failures  {s['parametric_failure_rate']:.2f}")
    for label, key in (("vs model-free null", "gp_beats_null_paired"),
                       ("vs polynomial PI  ", "gp_beats_poly_paired")):
        d, lo, hi, sig = s[key]
        print(f"  GP {label}: {d:+.4f} [{lo:+.4f}, {hi:+.4f}]  significant={sig}")


if __name__ == "__main__":
    main()
