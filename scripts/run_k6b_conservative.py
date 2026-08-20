"""K6b — joint certification via conservative excursion sets, and `alpha*`.

Registered in `docs/OPEN-QUESTIONS.md` (commit a35b1fc) before this file existed.
Additive to K6; K6 is not modified and its registered primary metric stands.

WHY JOINT
---------
`{x : LCB(x) >= tau}` is 20,000 marginal statements presented as one regional statement.
A batch record asserts the joint quantity: the probability that NO certified point is
false. Chevalier (2013); Azzimonti et al. (2016, SIAM/ASA JUQ 2021).

THE THRESHOLD, AND WHY THERE ARE FOUR OF THEM AND NOT TWENTY-FOUR
------------------------------------------------------------------
Margin 1 (process noise) collapses into the tau-as-fraction parameterisation exactly:
under relative noise, theta = tau/(1 - z*sigma_rel) and tau = tau_frac*tau_max with
tau_max = mu_max(1 - z*sigma_rel), so **theta = tau_frac * mu_max for every gamma**.
Checked to machine precision before this runner was written. gamma re-enters only as
interpretation -- at a given tau_frac, the absolute tau promisable at content level gamma
is tau_frac*tau_max(gamma).

SAMPLING, NOT ORTHANT PROBABILITIES
------------------------------------
The joint covariance is 3.2 GB at 20,000 grid points but **0.14 s at 2,000** (measured).
So the joint draw is taken on a 2,000-point subset -- a Monte Carlo approximation of the
same object, which is the fallback Azzimonti's own subset-selection mitigation implies.
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from boec.norms import sobol_grid
from boec.replay import committed_rows, instance_by_id, regenerate, unit_bounds
from boec.surrogate import build_gp
from boec.torch_oracle import BiphasicOracle
from boec.vorobev import (alpha_star, conservative_estimate, containment_probability,
                          excursion_probability, vorobev_deviation, vorobev_expectation)

OUT = Path("results/k6b-conservative.json")
GATE = Path("results/k1-replay-gate.json")

ARMS = ("doe", "qlogei", "qlognei", "qlogei-add", "qlogei-addonly")
#: theta = tau_frac * mu_max. Matches K6's tau_frac grid exactly -- see module docstring.
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
ALPHAS = (0.50, 0.80, 0.95)
#: 2,000 keeps the joint covariance at 32 MB / 0.14 s. At 20,000 it is 3.2 GB.
SUBSET_N = 2_000
N_DRAWS = 512
GRID_SEED = 0
JITTER = 1e-8


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def _gate_tol(arm: str) -> float:
    """The tolerance MEASURED by K1-gate. Never a constant chosen here."""
    if not GATE.exists():
        return 0.0
    return float(json.loads(GATE.read_text())
                 .get("policy", {}).get(arm, {}).get("worst_abs_delta", 0.0))


def joint_draws(model, X: torch.Tensor, n_draws: int = N_DRAWS,
                seed: int = 0) -> torch.Tensor:
    """``(n_draws, n)`` joint posterior samples via Cholesky of the full covariance."""
    with torch.no_grad():
        post = model.posterior(X)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + JITTER * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], n_draws, generator=g, dtype=torch.double)
        return (post.mean.reshape(-1, 1).double() + L @ z).T


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=6)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--arms", type=str, default=None)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    global ARMS, OUT
    if args.arms:
        ARMS = tuple(a.strip() for a in args.arms.split(","))
    if args.out:
        OUT = Path(args.out)

    head = _head()
    print(f"K6b · conservative excursion sets · HEAD={head}")
    print(f"cell d={args.dim} sigma={args.sigma} · arms={ARMS}")
    print(f"theta = tau_frac * mu_max, tau_frac={TAU_FRACS} (margin 1 absorbed)")
    print(f"subset={SUBSET_N} Sobol seed {GRID_SEED} · {N_DRAWS} joint draws\n")

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == args.dim and r["sigma"] == args.sigma
                   and r["arm"] == "qlogei"})
    if args.limit:
        keys = keys[:args.limit]
    committed = {(r["instance"], r["seed"], r["arm"]): r["regret"]
                 for r in committed_rows()
                 if r["dim"] == args.dim and r["sigma"] == args.sigma}
    print(f"{len(keys)} pairs x {len(ARMS)} arms = {len(keys)*len(ARMS)} campaigns\n")

    X_sub = sobol_grid(args.dim, SUBSET_N, seed=GRID_SEED)
    rows, gate_fail = [], []
    t0 = time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, args.dim)
        orc = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
        with torch.no_grad():
            truth = orc.truth(X_sub).reshape(-1).double()
        mu_max = float(inst.optimum_value)

        for arm in ARMS:
            t = time.time()
            rec = regenerate(inst_id, args.dim, args.sigma, seed, arm)
            ref = committed.get((inst_id, seed, arm))
            if ref is not None and abs(rec.regret - ref) > _gate_tol(arm):
                gate_fail.append({"instance": inst_id, "seed": seed, "arm": arm,
                                  "abs_delta": abs(rec.regret - ref)})
                print(f"  !! GATE {arm} {inst_id} seed={seed}")

            model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(args.dim))
            draws = joint_draws(model, X_sub, seed=seed)

            for tf in TAU_FRACS:
                theta = tf * mu_max
                p = excursion_probability(draws, theta)
                q = vorobev_expectation(p, draws, theta)
                true_set = truth >= theta
                inter = int((q & true_set).sum())
                union = int((q | true_set).sum())
                row = {"instance": inst_id, "dim": args.dim, "sigma": args.sigma,
                       "seed": seed, "arm": arm, "regret": rec.regret,
                       "tau_frac": tf, "theta": theta,
                       "true_frac_above": float(true_set.double().mean()),
                       "alpha_star": alpha_star(draws, theta),
                       "vorobev_deviation": vorobev_deviation(draws, theta),
                       "vorobev_expectation_vol": float(q.double().mean()),
                       "iou_vorobev_expectation": (inter / union) if union else float("nan"),
                       "max_p": float(p.max())}
                for a in ALPHAS:
                    ce = conservative_estimate(draws, theta, a)
                    n_ce = int(ce.sum())
                    row[f"ce_vol_{a}"] = n_ce / ce.numel()
                    row[f"ce_empty_{a}"] = n_ce == 0
                    row[f"ce_false_in_{a}"] = (
                        float((truth[ce] < theta).double().mean()) if n_ce
                        else float("nan"))
                    row[f"ce_contain_{a}"] = (containment_probability(draws, ce, theta)
                                              if n_ce else float("nan"))
                rows.append(row)

            print(f"[{i:3d}/{len(keys)}] {arm:14s} {inst_id} seed={seed} "
                  f"a*={rows[-4]['alpha_star']:.3f}..{rows[-1]['alpha_star']:.3f} "
                  f"({time.time()-t:.1f}s)", flush=True)
            del model, draws
            gc.collect()

        OUT.write_text(json.dumps({
            "provenance": {"git_sha": head, "argv": sys.argv,
                           "python": platform.python_version()},
            "config": {"dim": args.dim, "sigma": args.sigma, "arms": list(ARMS),
                       "tau_fracs": list(TAU_FRACS), "alphas": list(ALPHAS),
                       "subset_n": SUBSET_N, "n_draws": N_DRAWS,
                       "grid_seed": GRID_SEED},
            "gate_failures": gate_fail, "rows": rows}, indent=2))
        del truth
        gc.collect()

    print(f"\n{len(rows)} rows in {time.time()-t0:.0f}s · gate failures: {len(gate_fail)}")
    if gate_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
