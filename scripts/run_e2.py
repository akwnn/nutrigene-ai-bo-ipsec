"""E2 — sample efficiency. Does Bayesian optimization find a better recipe, sooner?

OWNERSHIP: Person A. Reproduce with `python scripts/run_e2.py`.
Pre-registered in `configs/experiment/e2.yaml`, committed before this ran.

Seven arms on an identical budget of 48: qLogEI (primary), qLogNEI (Q5 secondary),
random, Sobol, Latin hypercube, coordinate descent (Q3), and the sequential-DoE
pipeline that the published study actually used.

**Regret is scored on the NOISELESS value of the point each method selected** — see
OPEN-QUESTIONS Q17, decided before any E2 number existed. E1 demonstrated the bias is
real rather than theoretical: Branin's BO best-so-far read better than the true optimum.
It does not cancel across arms, because the inflation grows with how many distinct
high-value points an arm samples and that differs by arm by design.

**Inference clusters on instances, not runs.** 25 landscapes x 2 seeds has an effective
n of 25. This project criticises the source paper for pseudo-replication; making the
same mistake here would be indefensible.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from scipy.stats import wilcoxon

from boec.baselines import coordinate_descent
from boec.campaign import Campaign, CampaignConfig
from boec.diagnostics import instance_bootstrap, reported_best_curve
from boec.doe import run_doe_arm
from boec.oracles import load_ensemble
from boec.optimizers import AcqConfig, lhs_design, random_design, sobol_design
from boec.torch_oracle import BiphasicOracle

# --- PRE-REGISTERED (configs/experiment/e2.yaml). Do not edit after seeing results. ---
DIMS = (6, 8)
SIGMAS = (0.25, 0.10)          # 0.25 primary
N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
STATIC = {"random": random_design, "sobol": sobol_design, "lhs": lhs_design}


def unit_bounds(d):
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def scored_curve(orc, X: torch.Tensor, Y: torch.Tensor) -> np.ndarray:
    """Pick by what the method SAW, score by what was really there. Q17.

    NOT the best true value among visited points: that credits an arm for stumbling
    onto a recipe it could not identify, and the credit grows with how many scattered
    points the arm visits -- so space-filling arms win by construction. E2's first run
    used that definition and the tell was unmissable: the static arms came out
    completely noise-independent, identical at sigma_rel 0.25 and 0.10.
    """
    return reported_best_curve(orc.truth(X), Y)


def static_curve(orc, bounds, maker, budget, seed, n_orderings=20) -> np.ndarray:
    """Non-adaptive arm, averaged over random orderings, scored on truth.

    A one-shot design has no natural running order, so a best-so-far curve read off an
    arbitrary one is meaningless -- put the winner first and it looks brilliant.
    """
    X = maker(bounds, budget, seed=seed)
    Y, _ = orc.evaluate(X)
    rng = np.random.default_rng(seed)
    curves = []
    for _ in range(n_orderings):
        p = rng.permutation(budget)
        curves.append(scored_curve(orc, X[p], Y[p]))
    return np.stack(curves).mean(axis=0)


def run_cell(inst, dim, sigma, seed) -> dict:
    bounds = unit_bounds(dim)
    out: dict[str, np.ndarray] = {}

    for arm in ("qlogei", "qlognei"):
        orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        cfg = CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed,
                             acq=AcqConfig(kind=arm))
        c = Campaign(orc, bounds, cfg)
        c.run()
        out[arm] = scored_curve(orc, c.train_X, c.train_Y)

    for arm, maker in STATIC.items():
        out[arm] = static_curve(BiphasicOracle(inst, sigma_rel=sigma, seed=seed),
                                bounds, maker, BUDGET, seed)

    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cd = coordinate_descent(orc, bounds, budget=BUDGET, seed=seed)
    out["coord"] = scored_curve(orc, cd.X, cd.Y)

    # DoE arm is d=6 only: its 20 + 27 + 1 split is defined at six factors, and a d=8
    # screen needs its own budget arithmetic, which is a separate decision (Q15).
    if dim == 6:
        orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        r = run_doe_arm(orc, bounds, truth=orc.truth, budget=BUDGET, seed=seed)
        out["doe"] = scored_curve(orc, r.X_visited, r.Y_visited)
    return out


def main() -> None:
    rows = []
    for dim in DIMS:
        ens = load_ensemble(dim=dim)[:N_INSTANCES]
        for sigma in SIGMAS:
            for inst in ens:
                for seed in range(N_SEEDS):
                    curves = run_cell(inst, dim, sigma, seed)
                    for arm, curve in curves.items():
                        n_init = 14 if dim == 6 else 18
                        rows.append(dict(
                            instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                            arm=arm,
                            best=float(curve[-1]),
                            regret=float(inst.optimum_value - curve[-1]),
                            auc_post_init=float(np.trapezoid(curve[n_init:])
                                                / max(len(curve) - n_init - 1, 1)),
                        ))
            print(f"  d={dim} sigma={sigma} done ({len(rows)} rows)", flush=True)

    Path("results").mkdir(exist_ok=True)
    Path("results/e2-grid.json").write_text(json.dumps(rows, indent=1))
    report(rows)


def report(rows) -> None:
    arms = ["qlogei", "qlognei", "random", "sobol", "lhs", "coord", "doe"]
    for dim in DIMS:
        for sigma in SIGMAS:
            sub = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma]
            if not sub:
                continue
            insts = sorted({r["instance"] for r in sub})
            tag = " <-- PRIMARY CELL" if (dim == 6 and sigma == 0.25) else ""
            print(f"\n{'=' * 84}\nE2 · d={dim} · sigma_rel={sigma} · "
                  f"{len(insts)} instances x {N_SEEDS} seeds{tag}\n{'=' * 84}")
            print(f"{'arm':>9} {'simple regret (median [IQR])':>34} "
                  f"{'AUC post-init':>15}")
            per_arm = {}
            for a in arms:
                vals = [r["regret"] for r in sub if r["arm"] == a]
                if not vals:
                    continue
                # one number per instance, averaged over seeds -- effective n = 25
                per_arm[a] = np.array([
                    np.mean([r["regret"] for r in sub
                             if r["arm"] == a and r["instance"] == i]) for i in insts])
                auc = [r["auc_post_init"] for r in sub if r["arm"] == a]
                q1, q3 = np.percentile(vals, [25, 75])
                print(f"{a:>9} {np.median(vals):>14.4f}  [{q1:>7.4f},{q3:>8.4f}] "
                      f"{np.median(auc):>15.4f}")

            if "qlogei" in per_arm:
                others = [a for a in per_arm if a != "qlogei"]
                best_non_bo = min((a for a in others if a not in ("qlognei",)),
                                  key=lambda a: per_arm[a].mean(), default=None)
                print(f"\n  paired vs qLogEI, instance-level (n={len(insts)}):")
                for a in others:
                    d_ = per_arm[a] - per_arm["qlogei"]     # >0 means qLogEI has less regret
                    m, lo, hi = instance_bootstrap(d_, n_boot=2000)
                    try:
                        p = wilcoxon(d_).pvalue
                    except ValueError:
                        p = float("nan")
                    star = "  <-- best non-BO" if a == best_non_bo else ""
                    print(f"    {a:>9}: {m:>+8.4f}  [{lo:>+8.4f}, {hi:>+8.4f}]  "
                          f"wilcoxon p={p:.4f}{star}")


if __name__ == "__main__":
    main()
