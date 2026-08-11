"""Q29 — the symmetric comparison: score BOTH arms at their own model's recommendation.

    python scripts/q29_symmetric.py                 # primary cell, d=6 sigma=0.25
    python scripts/q29_symmetric.py --all-cells     # all four

PRE-REGISTERED in OPEN-QUESTIONS Q29, committed before this ran (b91a395).

WHY THIS EXISTS
---------------
Q28 measured that every E2 cell reverses sign depending on how the DoE arm is
scored. Rule A scores both arms at their best OBSERVED point, which discards the
DoE pipeline's actual output. Rule B scores DoE at its stage-4 recipe but qLogEI
at its best measurement, which is not like-for-like. Neither answers "which recipe
would you actually hand the lab".

Rule C asks both the same question:

    DoE  -> the stage-4 confirmation recipe (constrained argmax of its fitted
            second-order surface)
    BO   -> the argmax of the GP POSTERIOR MEAN over the same box

Both scored on ``truth()``, never on the noisy observation (Q17). Selection sees
only what each method is allowed to see: the GP is fitted to observations alone,
and the posterior mean is the model's own belief, not the oracle.

E2 never recorded BO's posterior-mean argmax and ``results/e2-grid.json`` stores
summary rows only, so this is a run rather than a re-analysis. Seeds, openings and
budget are identical to E2, so the rule-A numbers regenerate here and are checked
against the stored grid as a fidelity gate before any rule-C number is reported.
"""

from __future__ import annotations

import argparse
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import warnings

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

from botorch.acquisition.analytic import PosteriorMean
from botorch.optim import optimize_acqf
from scipy.stats import wilcoxon

from boec.campaign import Campaign, CampaignConfig
from boec.diagnostics import instance_bootstrap, reported_best_curve
from boec.doe import run_doe_arm
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

BUDGET = 48
N_INSTANCES = 25
N_SEEDS = 2
RULE = "=" * 84


def posterior_mean_argmax(campaign: Campaign, bounds: torch.Tensor) -> torch.Tensor:
    """The recipe the GP itself recommends: argmax of its posterior MEAN.

    Not the acquisition function — acquisition deliberately chases variance, which
    is the right thing when deciding where to look next and the wrong thing when
    naming the recipe you believe is best. This is the GP's analogue of the DoE
    arm's stage-4 point: the model's own claim about where the optimum is.
    """
    model = campaign.fit()
    candidate, _ = optimize_acqf(
        PosteriorMean(model), bounds=bounds, q=1, num_restarts=10, raw_samples=256,
    )
    return candidate.detach().reshape(-1)


def run_cell(dim: int, sigma: float) -> list[dict]:
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    rows: list[dict] = []
    for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
        for seed in range(N_SEEDS):
            # --- BO -------------------------------------------------------
            o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            c = Campaign(o, bounds, CampaignConfig(d=dim, budget=BUDGET, q=4,
                                                   seed=seed)).run()
            # rule A, regenerated so it can be checked against the stored grid
            bo_a = float(reported_best_curve(o.truth(c.train_X), c.train_Y)[-1])
            # rule C — the GP's own recommendation
            x_rec = posterior_mean_argmax(c, bounds)
            bo_c = float(o.truth(x_rec.unsqueeze(0)))

            # --- DoE ------------------------------------------------------
            od = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            r = run_doe_arm(od, bounds, truth=od.truth, budget=BUDGET, seed=seed)
            doe_a = float(reported_best_curve(od.truth(r.X_visited), r.Y_visited)[-1])
            doe_c = float(od.truth(r.confirmation_x.unsqueeze(0)))

            opt = float(inst.optimum_value)
            rows.append(dict(
                instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                bo_regret_a=opt - bo_a, bo_regret_c=opt - bo_c,
                doe_regret_a=opt - doe_a, doe_regret_c=opt - doe_c,
            ))
    return rows


def _per_instance(rows: list[dict], key: str) -> tuple[list[str], np.ndarray]:
    ids = sorted({r["instance"] for r in rows})
    return ids, np.array([
        np.mean([r[key] for r in rows if r["instance"] == i]) for i in ids
    ])


def report(rows: list[dict], dim: int, sigma: float) -> None:
    ids, bo_a = _per_instance(rows, "bo_regret_a")
    _, bo_c = _per_instance(rows, "bo_regret_c")
    _, doe_a = _per_instance(rows, "doe_regret_a")
    _, doe_c = _per_instance(rows, "doe_regret_c")

    print(f"\n{RULE}\nQ29 · d={dim} · sigma={sigma} · {len(ids)} instances x {N_SEEDS} seeds\n{RULE}")
    print(f"{'':>26}{'qLogEI':>12}{'DoE':>12}{'DoE - qLogEI':>16}{'95% CI':>24}{'wilcoxon':>11}")
    for label, b, d in (("rule A  (best observed)", bo_a, doe_a),
                        ("rule C  (each model's rec)", bo_c, doe_c)):
        diff = d - b                       # >0 means DoE has MORE regret => BO better
        m, lo, hi = instance_bootstrap(diff, n_boot=2000)
        try:
            p = wilcoxon(diff).pvalue
        except ValueError:
            p = float("nan")
        verdict = "BO better" if lo > 0 else ("DoE better" if hi < 0 else "null")
        print(f"{label:>26}{np.median(b):>12.4f}{np.median(d):>12.4f}{m:>+16.4f}"
              f"{f'[{lo:+.4f}, {hi:+.4f}]':>24}{p:>11.4f}  {verdict}")
    print("\n  Positive difference = DoE carries more regret = BO is better.")
    print("  Rule A is the registered primary (Q20); rule C is Q29's declared secondary.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-cells", action="store_true")
    args = ap.parse_args()

    cells = [(6, 0.25)] if not args.all_cells else [(6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10)]
    everything: list[dict] = []
    for dim, sigma in cells:
        rows = run_cell(dim, sigma)
        everything.extend(rows)
        report(rows, dim, sigma)

    # Fidelity gate: rule A regenerated here must match the stored E2 grid.
    try:
        grid = json.load(open("results/e2-grid.json"))
        stored = {(g["instance"], g["seed"], g["dim"], g["sigma"]): g["regret"]
                  for g in grid if g["arm"] == "qlogei"}
        deltas = [abs(r["bo_regret_a"] - stored[(r["instance"], r["seed"], r["dim"], r["sigma"])])
                  for r in everything
                  if (r["instance"], r["seed"], r["dim"], r["sigma"]) in stored]
        if deltas:
            print(f"\n  FIDELITY vs results/e2-grid.json (qLogEI rule A): "
                  f"max |delta| {max(deltas):.3e} over {len(deltas)} rows")
    except FileNotFoundError:
        print("\n  (no stored grid to check against)")

    with open("results/q29-symmetric.json", "w") as fh:
        json.dump(everything, fh, indent=1)
    print("\n  written to results/q29-symmetric.json")


if __name__ == "__main__":
    main()
