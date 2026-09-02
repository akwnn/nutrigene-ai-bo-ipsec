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
from pathlib import Path

import numpy as np
import torch

torch.set_num_threads(1)
warnings.filterwarnings("ignore")

from boec.e4 import E4Config, run_e4_cell, summarise
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

KAPPAS = (0.6, 0.7, 0.8, 0.9)
RULE = "=" * 72


def verdict(lo: float, hi: float) -> str:
    """A three-way reading of a paired interval, replacing ``significant={bool}``.

    **Q19.** ``paired_difference_ci``'s ``is_significant`` is one-sided by design --
    its docstring says "True only when the whole interval sits above zero", because
    the registered question is whether the GP BEATS the null. Printing that as
    ``significant=False`` was accurate about the flag and misleading about the data:
    at kappa=0.8 and 0.9 the intervals are [-0.145, -0.047] and [-0.148, -0.056],
    entirely clear of zero, and the line read as "nothing here" next to two of the
    strongest effects on the grid. Anyone scanning the log would conclude the
    opposite of what it shows.

    The flag is unchanged; only the report is. A one-sided test is the right test
    for the registered claim, but the reader has to be told which direction it
    can see.
    """
    if lo > 0:
        return "GP BETTER — interval clears zero"
    if hi < 0:
        return "GP WORSE — interval clears zero"
    return "null — interval spans zero"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=6, help="E4 is d=6 only; see spec §6")
    ap.add_argument("--instances", type=int, default=25,
                    help="PRE-REGISTERED at 25 (v2). 40 needs A to extend the ensemble.")
    ap.add_argument("--rho", type=float, default=2.0,
                    help="PRE-REGISTERED primary is 2.0. Pass inf for the limiting case.")
    ap.add_argument("--kappas", type=float, nargs="+", default=list(KAPPAS))
    args = ap.parse_args()

    # Refuse to silently run something other than the pre-registration.
    import yaml
    cfg_path = Path(__file__).resolve().parents[1] / "configs" / "experiment" / "e4.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    for name, got, want in (("--instances", args.instances, cfg["n_instances"]),
                            ("--rho", args.rho, cfg["rho"])):
        if got != want:
            print(f"\n!!! {name}={got} deviates from the pre-registered {want}.")
            print("!!! Bump preregistration_version and state the reason.\n")

    instances = load_ensemble(args.dim)[: args.instances]
    regime = "unit cube (limiting case)" if args.rho == float("inf") else f"rho={args.rho} (PRE-REGISTERED PRIMARY)"
    print(f"{len(instances)} instances at d={args.dim}, kappa in {args.kappas}, {regime}")

    t0 = time.perf_counter()
    results = []
    for kappa in args.kappas:
        for i, inst in enumerate(instances):
            results.append(
                run_e4_cell(
                    BiphasicOracle(inst),
                    E4Config(kappa=kappa, rho=args.rho, seed=i),
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

    # Q19: this block is the discrimination result BY KAPPA. The registered primary
    # is a single cell -- configs/experiment/e4.yaml:106, primary_cell {kappa: 0.6,
    # rho: 2.0} -- not this table and not the pooled figure below it. Labelling the
    # whole block "the pre-registered primary" is how the pooled number came to be
    # reported under that name in E4-RESULTS-v2.md while disagreeing with it in sign.
    print("\n" + RULE, "\nDISCRIMINATION by kappa "
          "(registered primary CELL is kappa=0.6; pooled is NOT the primary)\n",
          RULE, sep="")
    for k in args.kappas:
        sub = [r for r in valid if r.kappa == k]
        if not sub:
            continue
        s = summarise(sub)
        gp, nn = s["spearman_gp"], s["spearman_nearest_neighbour"]
        d, lo, hi, sig = s["gp_beats_null_paired"]
        print(f"  kappa={k}: GP rho {gp[0]:+.3f} | nearest-neighbour rho {nn[0]:+.3f}")
        print(f"           PAIRED difference {d:+.4f} [{lo:+.4f}, {hi:+.4f}]  {verdict(lo, hi)}")

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
        print(f"  GP {label}: {d:+.4f} [{lo:+.4f}, {hi:+.4f}]  {verdict(lo, hi)}")
    exact = s["gp_beats_null_exact_is_enumerated"]
    label = "EXACT (all arrangements enumerated)" if exact else "sampled, not exact"
    print(f"  sign-flip test     : p={s['gp_beats_null_exact_p']:.4f}  [{label}]")
    print(f"  advantage bounded  : {s['gp_advantage_verdict']}")


if __name__ == "__main__":
    main()
