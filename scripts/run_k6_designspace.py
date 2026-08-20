"""K6 — does the design-space deliverable rank the arms differently from simple regret?

Registered in `docs/OPEN-QUESTIONS.md` (commit ef118dd) before this file existed.

WHAT THIS IS FOR
----------------
Every headline in this project scores a campaign by the regret of a single nominated
point. A batch record is not a point; it is a *range per factor*. This asks whether the
two objects rank the arms the same way. If they do, the reframe adds nothing and SPADE
Stages 4-5 are dropped. If they diverge with the spread arm ahead, Version B is built.

THE PRIMARY OBJECT IS PETERSON'S D_gamma
----------------------------------------
`D_gamma = {x : P(Y >= tau | x) >= gamma}` on the posterior PREDICTIVE. The latent map is
computed alongside as secondary: E3 measured latent coverage at 0.7644 against nominal
0.95 while predictive recovers to ~0.90-0.92, so the GAP between the two maps is itself
the result, and it is the one a certificate would be built on.

tau IS A FRACTION OF tau_max, NEVER ABSOLUTE
---------------------------------------------
`tau_max = mu_max(1 - z*sigma_rel)` = 0.589 at sigma_rel=0.25, gamma=0.95, at ANY budget.
An absolute grid above that certifies nothing for any arm and returns a table of zeros.

AMENDMENT A1: Q30's kernel arms are included, so the same intervention can be scored on
both deliverables. Q30 measured 2x held-out R-squared buying dRegret 0.0015, p=0.71. If
those arms gain materially on the map, that is the cleanest figure the project can make.
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

from boec.designspace import (brier_and_auc, false_inclusion_rate, gp_adapter,
                              inscribed_box_from_mask, iou,
                              predictive_probability_map, probability_map, tau_max)
from boec.norms import grid_r2, sobol_grid, sup_err
from boec.replay import committed_rows, instance_by_id, regenerate, unit_bounds
from boec.surrogate import build_gp
from boec.torch_oracle import BiphasicOracle

OUT = Path("results/k6-designspace.json")
GATE = Path("results/k1-replay-gate.json")

ARMS = ("doe", "qlogei", "qlognei", "qlogei-add", "qlogei-addonly")
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
GRID_N = 20_000
GRID_SEED = 0


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def _gate_tol(arm: str) -> float:
    """The tolerance measured by K1-gate. Never a constant chosen here."""
    if not GATE.exists():
        return 0.0
    pol = json.loads(GATE.read_text()).get("policy", {})
    return float(pol.get(arm, {}).get("worst_abs_delta", 0.0))


def score_campaign(rec, orc, grid, truth, active) -> list[dict]:
    """Every (gamma, tau) metric for one regenerated campaign."""
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))
    # CHUNKED. model.posterior over the whole 20k grid builds the joint covariance and
    # takes 100.6s against 0.06s at 2k -- see boec.designspace.gp_adapter.
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, X):
            return mean, sd

    m = _M()
    # A lab does not know f, so the predictive SD is a PLUG-IN from the posterior mean.
    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    rows = []
    base = {"instance": rec.instance, "dim": rec.dim, "sigma": rec.sigma,
            "seed": rec.seed, "arm": rec.arm, "regret": rec.regret,
            "sup_err": sup_err(m, lambda X: truth, grid),
            "grid_r2": grid_r2(m, lambda X: truth, grid)}

    for gamma in GAMMAS:
        tmax = tau_max(gamma, orc.sigma_rel)
        for tf in TAU_FRACS:
            tau = round(tf * tmax, 10)
            p_pred = predictive_probability_map(m, grid, tau, sigma_pred)
            p_lat = probability_map(m, grid, tau)
            d_gamma = p_pred >= gamma
            latent = p_lat >= gamma
            true_set = truth.reshape(-1) >= tau

            b_pred, a_pred = brier_and_auc(p_pred, truth, tau)
            b_lat, a_lat = brier_and_auc(p_lat, truth, tau)
            _, box_vol = inscribed_box_from_mask(grid, d_gamma, active=active,
                                                 seed_score=p_pred)
            rows.append({**base, "gamma": gamma, "tau_frac": tf, "tau": tau,
                         "tau_max": tmax,
                         "true_frac_above_tau": float(true_set.double().mean()),
                         "vol_pred": float(d_gamma.double().mean()),
                         "vol_latent": float(latent.double().mean()),
                         "empty_pred": int(d_gamma.sum()) == 0,
                         "empty_latent": int(latent.sum()) == 0,
                         "iou_pred": iou(d_gamma, truth, tau),
                         "iou_latent": iou(latent, truth, tau),
                         "fi_pred": false_inclusion_rate(d_gamma, truth, tau),
                         "fi_latent": false_inclusion_rate(latent, truth, tau),
                         "brier_pred": b_pred, "auc_pred": a_pred,
                         "brier_latent": b_lat, "auc_latent": a_lat,
                         "box_vol_pred": box_vol,
                         "n_active": int(active.sum())})
    del model, mean, sd
    gc.collect()
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=6)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=None,
                    help="instances to score; default all")
    args = ap.parse_args()

    head = _head()
    print(f"K6 · design space vs regret · HEAD={head} · python={platform.python_version()}")
    print(f"cell d={args.dim} sigma={args.sigma} · arms={ARMS}")
    print(f"gamma={GAMMAS}\ntau_frac={TAU_FRACS} (of tau_max, never absolute)")
    print(f"grid: {GRID_N} Sobol at seed {GRID_SEED}\n")

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == args.dim and r["sigma"] == args.sigma
                   and r["arm"] == "qlogei"})
    if args.limit:
        keys = keys[:args.limit]
    print(f"{len(keys)} (instance, seed) pairs x {len(ARMS)} arms "
          f"= {len(keys)*len(ARMS)} campaigns\n")

    committed = {(r["instance"], r["seed"], r["arm"]): r["regret"]
                 for r in committed_rows()
                 if r["dim"] == args.dim and r["sigma"] == args.sigma}
    grid = sobol_grid(args.dim, GRID_N, seed=GRID_SEED)

    rows: list[dict] = []
    gate_fail: list[dict] = []
    t0 = time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, args.dim)
        orc = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
        with torch.no_grad():
            truth = orc.truth(grid).reshape(-1).double()

        for arm in ARMS:
            t = time.time()
            rec = regenerate(inst_id, args.dim, args.sigma, seed, arm)

            ref = committed.get((inst_id, seed, arm))
            if ref is not None:
                delta = abs(rec.regret - ref)
                if delta > _gate_tol(arm):
                    gate_fail.append({"instance": inst_id, "seed": seed, "arm": arm,
                                      "committed": ref, "regenerated": rec.regret,
                                      "abs_delta": delta})
                    print(f"  !! GATE {arm} {inst_id} seed={seed} delta={delta:.3e}")

            active = torch.zeros(args.dim, dtype=torch.bool)
            if rec.kept_factors is None:
                active[:] = True
            else:
                active[list(rec.kept_factors)] = True

            rows.extend(score_campaign(rec, orc, grid, truth, active))
            print(f"[{i:3d}/{len(keys)}] {arm:14s} {inst_id} seed={seed} "
                  f"regret={rec.regret:.4f} active={int(active.sum())} "
                  f"({time.time()-t:.1f}s)", flush=True)

        OUT.write_text(json.dumps({
            "provenance": {"git_sha": head, "argv": sys.argv,
                           "python": platform.python_version()},
            "config": {"dim": args.dim, "sigma": args.sigma, "arms": list(ARMS),
                       "gammas": list(GAMMAS), "tau_fracs": list(TAU_FRACS),
                       "grid_n": GRID_N, "grid_seed": GRID_SEED},
            "gate_failures": gate_fail, "rows": rows}, indent=2))
        del truth
        gc.collect()

    print(f"\n{len(rows)} scored rows in {time.time()-t0:.0f}s")
    print(f"gate failures: {len(gate_fail)}")
    if gate_fail:
        print("*** Regenerated campaigns did not reproduce. Results are NOT comparable. ***")
        sys.exit(1)


if __name__ == "__main__":
    main()
