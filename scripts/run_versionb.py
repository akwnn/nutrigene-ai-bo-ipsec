"""Version B — the two-plate arm. The test that can actually settle SPADE.

Registered in `docs/OPEN-QUESTIONS.md` before `src/boec/lse.py` existed.

K6 and K6b tested plate 1 only. SPADE v2 is two plates, so plate 1 losing to qLogNEI in
15 of 24 cells does not settle it. Plate 2 is the machinery meant to repair a weak
certified region and it had never been run.

BUDGET: 40 + 8 = 48. The second plate comes OUT of the design, never on top. Any
comparison that adds wells is not budget-matched and must not be a headline.

ROUNDS ARE REPORTED. Every K6 contrast was at equal wells only. plate1_only is 1 round,
versionb is 2, doe is 3, qlognei is 10.
"""

from __future__ import annotations

import argparse, gc, json, platform, subprocess, sys, time
from pathlib import Path

import numpy as np
import torch

from boec.designspace import gp_adapter, brier_and_auc, predictive_probability_map
from boec.lse import batch_lse, exclusion_radius
from boec.norms import sobol_grid
from boec.replay import committed_rows, instance_by_id, regenerate, scored_curve, unit_bounds
from boec.runner import static_design
from boec.surrogate import build_gp
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar
from boec.vorobev import (alpha_star, conservative_estimate, containment_probability,
                          empirical_containment, excursion_probability, vorobev_deviation)

OUT = Path("results/versionb.json")
N_PLATE1, N_PLATE2, BUDGET = 40, 8, 48
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
#: Threshold the LSE criterion TARGETS. Registered; scoring still spans all TAU_FRACS.
DESIGN_TAU_FRAC = 0.75
GAMMA_FOR_AUC = 0.90
GRID_N, SUBSET_N, N_DRAWS, GRID_SEED = 20_000, 2_000, 512, 0
ALPHAS = (0.50, 0.80, 0.95)
ROUNDS = {"versionb": 2, "versionb_random": 2, "plate1_only": 1, "doe": 3, "qlognei": 10}


def _head():
    return subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()


def _fit(X, Y, Yvar, d):
    return build_gp(X, Y, Yvar, unit_bounds(d))


def _two_plate(orc, dim, seed, mu_max, use_lse: bool):
    """Plate 1 space-filling, plate 2 by LSE or at random. Returns (X, Y, Yvar)."""
    bounds = unit_bounds(dim)
    X1 = static_design(bounds, "lhs", N_PLATE1, seed)
    Y1, V1 = orc.evaluate(X1)
    model = _fit(X1, Y1, V1, dim)

    if use_lse:
        cand = sobol_grid(dim, 4096, seed=seed)
        theta = DESIGN_TAU_FRAC * mu_max
        X2 = batch_lse(gp_adapter(model), cand, theta, N_PLATE2,
                       exclude=exclusion_radius(model))
    else:
        g = torch.Generator().manual_seed(10_000 + seed)
        X2 = torch.rand(N_PLATE2, dim, generator=g, dtype=torch.double)

    Y2, V2 = orc.evaluate(X2)
    del model; gc.collect()
    return torch.cat([X1, X2]), torch.cat([Y1, Y2]), torch.cat([V1, V2])


def _score(X, Y, Yvar, orc, dim, mu_max, grid, truth, X_sub, truth_sub, seed,
           kept=None, held=None):
    """Score one campaign. `kept`/`held` apply Amendment B3: an arm that never varied a
    factor is evaluated on its ACTIVE SUBSPACE, with screened-out coordinates pinned."""
    model = _fit(X, Y, Yvar, dim)
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, Z): return mean, sd

    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    X_eval = X_sub
    t_eval = truth_sub
    if kept is not None and held:
        X_eval = X_sub.clone()
        for j, v in held.items():
            X_eval[:, j] = v
        with torch.no_grad():
            t_eval = orc.truth(X_eval).reshape(-1).double()

    with torch.no_grad():
        post = model.posterior(X_eval)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], N_DRAWS, generator=g, dtype=torch.double)
        draws = (post.mean.reshape(-1, 1).double() + L @ z).T

    out = {"regret": float(mu_max - scored_curve(orc, X, Y)[-1]), "n_wells": int(X.shape[0]),
           "n_active": dim if kept is None else len(kept)}
    for tf in TAU_FRACS:
        theta = tf * mu_max
        p = predictive_probability_map(_M(), grid, theta, sigma_pred)
        b, a = brier_and_auc(p, truth, theta)
        out[f"auc_{tf}"] = a
        out[f"brier_{tf}"] = b
        out[f"alpha_star_{tf}"] = alpha_star(draws, theta)
        out[f"vorobev_dev_{tf}"] = vorobev_deviation(draws, theta)
        for a in ALPHAS:
            ce = conservative_estimate(draws, theta, a)
            n_ce = int(ce.sum())
            out[f"ce_vol_{tf}_{a}"] = n_ce / ce.numel()
            out[f"ce_empty_{tf}_{a}"] = n_ce == 0
            # CIRCULAR -- conservative_estimate selects on this. Kept, labelled, so the
            # tautology is visible rather than silently removed.
            out[f"ce_contain_{tf}_{a}"] = (containment_probability(draws, ce, theta)
                                           if n_ce else float("nan"))
            # THE REAL TEST: is the set actually inside the TRUE excursion set?
            emp = empirical_containment(ce, t_eval, theta)
            out[f"ce_empirical_{tf}_{a}"] = float("nan") if emp is None else float(emp)
    del model, draws, mean, sd; gc.collect()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=6)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    head = _head()
    print(f"Version B · two-plate SPADE · HEAD={head}")
    print(f"{N_PLATE1} + {N_PLATE2} = {N_PLATE1+N_PLATE2} wells · LSE targets "
          f"tau_frac={DESIGN_TAU_FRAC} · rounds {ROUNDS}\n")

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == args.dim and r["sigma"] == args.sigma
                   and r["arm"] == "qlogei"})
    if args.limit: keys = keys[:args.limit]
    print(f"{len(keys)} instance-seeds\n")

    grid = sobol_grid(args.dim, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(args.dim, SUBSET_N, seed=GRID_SEED)
    rows, t0 = [], time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, args.dim)
        orc_t = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
        with torch.no_grad():
            truth = orc_t.truth(grid).reshape(-1).double()
            truth_sub = orc_t.truth(X_sub).reshape(-1).double()
        mu_max = float(inst.optimum_value)

        for arm in ("versionb", "versionb_random", "plate1_only", "doe", "qlognei"):
            t = time.time()
            kept = held = None
            orc = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
            if arm in ("versionb", "versionb_random"):
                X, Y, V = _two_plate(orc, args.dim, seed, mu_max, arm == "versionb")
            elif arm == "plate1_only":
                X = static_design(unit_bounds(args.dim), "lhs", BUDGET, seed)
                Y, V = orc.evaluate(X)
            else:
                rec = regenerate(inst_id, args.dim, args.sigma, seed, arm)
                X, Y, V = rec.X, rec.Y, rec.Yvar
                kept, held = rec.kept_factors, rec.dropped_held_at
            if arm != "doe":
                kept = held = None
            r = _score(X, Y, V, orc_t, args.dim, mu_max, grid, truth, X_sub, truth_sub,
                       seed, kept=kept, held=held)
            r.update({"instance": inst_id, "seed": seed, "arm": arm,
                      "rounds": ROUNDS[arm], "dim": args.dim, "sigma": args.sigma})
            rows.append(r)
            print(f"[{i:3d}/{len(keys)}] {arm:16s} {inst_id} seed={seed} "
                  f"n={r['n_wells']} rounds={ROUNDS[arm]:2d} regret={r['regret']:.4f} "
                  f"a*={r[f'alpha_star_{DESIGN_TAU_FRAC}']:.3f} ({time.time()-t:.1f}s)",
                  flush=True)

        OUT.write_text(json.dumps({
            "provenance": {"git_sha": head, "argv": sys.argv,
                           "python": platform.python_version()},
            "config": {"dim": args.dim, "sigma": args.sigma,
                       "n_plate1": N_PLATE1, "n_plate2": N_PLATE2,
                       "tau_fracs": list(TAU_FRACS),
                       "design_tau_frac": DESIGN_TAU_FRAC, "rounds": ROUNDS,
                       "alphas": list(ALPHAS),
                       "grid_n": GRID_N, "subset_n": SUBSET_N, "n_draws": N_DRAWS},
            "rows": rows}, indent=2))
        del truth, truth_sub; gc.collect()

    print(f"\n{len(rows)} rows in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
