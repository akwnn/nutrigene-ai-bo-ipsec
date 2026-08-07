"""Robustness checks E4's headline claims depend on. Spec Build Step 6 extension.

Three things the first run could not answer, all raised by adversarial audit:

1. **Is the difference BETWEEN regimes real?** Saying an effect is significant
   in one regime and not another does not establish the regimes differ — one
   can sit just inside a threshold and the other just outside while being
   statistically indistinguishable (Gelman & Stern 2006). The claim needs its
   own test, on the difference between the differences.

2. **Does averaging correlations bias the answer?** Correlations are not on an
   additive scale, so a plain average of them is biased. The standard fix is to
   transform, average, transform back. Reported alongside, not instead of.

3. **Was the sign-flip p-value exact?** Only up to 20 landscapes. Beyond that
   it samples, and the Monte Carlo error must be quoted with it.

    python scripts/run_e4_robustness.py
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import json
import time
import warnings

import numpy as np
import torch

torch.set_num_threads(1)
warnings.filterwarnings("ignore")

from boec.discrimination import (
    equivalence_bound_test,
    fisher_z_mean,
    regime_interaction_test,
    sign_flip_test,
)
from boec.e4 import E4Config, _aggregate_by_instance, run_e4_cell
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

KAPPAS = (0.6, 0.7, 0.8, 0.9)
BOUND = 0.08          # PRE-REGISTERED smallest advantage worth having
RULE = "=" * 72


def per_landscape_differences(instances, rho: float) -> dict[str, list]:
    """GP-minus-null, one number per landscape, under both aggregations."""
    results = [
        run_e4_cell(BiphasicOracle(o), E4Config(kappa=k, rho=rho, seed=i),
                    instance_id=o.instance_id[:8])
        for k in KAPPAS for i, o in enumerate(instances)
    ]
    raw_gp = _aggregate_by_instance(results, lambda r: r.discrimination.spearman["gp_predictive_sd"])
    raw_nn = _aggregate_by_instance(results, lambda r: r.discrimination.spearman["nearest_neighbour_distance"])

    z_gp: dict[str, list[float]] = {}
    z_nn: dict[str, list[float]] = {}
    for r in results:
        z_gp.setdefault(r.instance_id, []).append(r.discrimination.spearman["gp_predictive_sd"])
        z_nn.setdefault(r.instance_id, []).append(r.discrimination.spearman["nearest_neighbour_distance"])

    ids = sorted(set(raw_gp) & set(raw_nn))
    return {
        "ids": ids,
        "raw": [raw_gp[i] - raw_nn[i] for i in ids],
        "fisher_z": [fisher_z_mean(z_gp[i]) - fisher_z_mean(z_nn[i]) for i in ids],
        "n_cells": len(results),
        "n_valid": sum(1 for r in results if r.is_valid),
    }


def main() -> None:
    instances = load_ensemble(6)[:25]
    print(f"{len(instances)} landscapes, kappa in {KAPPAS}\n")

    t0 = time.perf_counter()
    store = {}
    for rho in (2.0, float("inf")):
        label = "rho=2.0 (PRIMARY)" if rho == 2.0 else "unit cube (limiting)"
        store[str(rho)] = per_landscape_differences(instances, rho)
        d = store[str(rho)]
        print(f"  {label:<22} {d['n_valid']}/{d['n_cells']} valid, "
              f"{len(d['ids'])} landscapes, raw mean {np.mean(d['raw']):+.4f} "
              f"({time.perf_counter() - t0:.0f}s)")

    print("\n" + RULE)
    print("1. IS THE DIFFERENCE BETWEEN REGIMES REAL?")
    print("   (two separate tests either side of a threshold do not establish this)")
    print(RULE)
    for agg in ("raw", "fisher_z"):
        m, lo, hi, differ = regime_interaction_test(store["inf"][agg], store["2.0"][agg])
        print(f"  [{agg:<8}] cube minus rho2: {m:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
              f"REGIMES DIFFER = {differ}")

    print("\n" + RULE)
    print("2. THE PRIMARY RESULT, UNDER BOTH AGGREGATIONS")
    print(RULE)
    for agg in ("raw", "fisher_z"):
        diffs = store["2.0"][agg]
        p, n, exact, se = sign_flip_test(diffs)
        _, below, verdict = equivalence_bound_test(diffs, BOUND)
        tag = "EXACT" if exact else f"sampled, MC se {se:.5f}"
        print(f"  [{agg:<8}] mean {np.mean(diffs):+.4f} | sign-flip p={p:.4f} [{tag}]")
        print(f"             {verdict}")

    print("\n" + RULE)
    print("3. SENSITIVITY: does the conclusion depend on the aggregation?")
    print(RULE)
    agree = (np.sign(np.mean(store["2.0"]["raw"])) == np.sign(np.mean(store["2.0"]["fisher_z"])))
    print(f"  primary regime, both aggregations agree in sign: {agree}")
    gap = abs(np.mean(store["2.0"]["raw"]) - np.mean(store["2.0"]["fisher_z"]))
    print(f"  absolute gap between aggregations: {gap:.4f} (bound is {BOUND})")
    print(f"  -> conclusion is {'ROBUST' if agree and gap < BOUND else 'SENSITIVE'} to the choice")

    out = "results/e4-robustness.json"
    json.dump({k: {kk: vv for kk, vv in v.items()} for k, v in store.items()},
              open(out, "w"), indent=2)
    print(f"\nper-landscape values written to {out}")


if __name__ == "__main__":
    main()
