"""EXPLORATORY Part A — is BO discarding its own model at the finish line?

**NOT REGISTERED. NOT A RESULT. NO NEW EVALUATIONS, NO CONFIGURATION CHANGE.**

    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/exploratory_recommendation.py

------------------------------------------------------------------------------
THE ASYMMETRY
------------------------------------------------------------------------------

The DoE arm's final answer comes from its MODEL: stage 3 fits the second-order
surface, stage 4 locates its optimum and spends one of the 48 evaluations
confirming it.

BO's final answer is its best OBSERVED point. No model involved. At sigma_rel =
0.25 that means reporting whichever point drew the luckiest reading -- while the
three-factor factorial measured this same GP's posterior mean at **RMS 0.137
against truth**, versus a single-observation noise of about 0.25. The model is
roughly twice as accurate as the measurement it is being scored on.

This is pure re-analysis of runs already on disk. Three true values per run:

  y_true_observed      truth at the best OBSERVED point -- what is reported now
  y_true_posterior     truth at the argmax of the posterior mean over the box
  y_true_best_visited  truth at the best point actually VISITED, by true value

The third is an oracle bound and is **not reportable as a method**. It exists to
say how much any recommendation rule could recover from the points BO chose. If
the posterior rule captures most of that gap, recommendation is the binding
constraint; if a large gap remains, BO's POINTS were poor and no reporting rule
fixes it -- which would support the coverage explanation instead.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import json                                      # noqa: E402
from multiprocessing import Pool                 # noqa: E402
from pathlib import Path                         # noqa: E402

import numpy as np                               # noqa: E402

DIM = 6
SIGMAS = (0.25, 0.10)          # 0.10 is the control: a noise-driven effect must shrink
N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
N_RESTARTS = 20                # generous: a poorly optimised argmax UNDERSTATES the effect
RAW_SAMPLES = 1024


def _row(task) -> dict:
    import torch

    torch.set_num_threads(1)

    from botorch.acquisition.analytic import PosteriorMean
    from botorch.optim import optimize_acqf

    from boec.campaign import Campaign, CampaignConfig
    from boec.diagnostics import reported_best_curve
    from boec.optimizers import AcqConfig
    from boec.oracles import load_ensemble
    from boec.surrogate import build_gp
    from boec.torch_oracle import BiphasicOracle

    sigma, i_inst, seed = task
    inst = load_ensemble(dim=DIM)[i_inst]
    bounds = torch.stack([torch.zeros(DIM, dtype=torch.double),
                          torch.ones(DIM, dtype=torch.double)])

    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    camp = Campaign(orc, bounds,
                    CampaignConfig(d=DIM, budget=BUDGET, q=4, seed=seed,
                                   acq=AcqConfig(kind="qlogei"))).run()

    truth = orc.truth(camp.train_X).detach().double().cpu().numpy().ravel()
    obs = camp.train_Y.detach().double().cpu().numpy().ravel()

    # 1. what is reported today: pick by observation, score by truth
    y_obs = float(reported_best_curve(orc.truth(camp.train_X), camp.train_Y)[-1])
    # 3. the oracle bound: the best point BO actually visited
    y_vis = float(truth.max())

    # 2. the model's own recommendation, over the whole box
    model = build_gp(camp.train_X, camp.train_Y, camp.train_Yvar, bounds)
    failed = False
    try:
        xh, _ = optimize_acqf(PosteriorMean(model), bounds=bounds, q=1,
                              num_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES)
    except Exception:                                        # noqa: BLE001
        failed = True
        xh = camp.train_X[int(np.argmax(obs))].unsqueeze(0)
    y_post = float(orc.truth(xh).detach().double().cpu().numpy().ravel()[0])

    Xn = camp.train_X.detach().double().cpu().numpy()
    xh_np = xh.detach().double().cpu().numpy().ravel()
    dists = np.linalg.norm(Xn - xh_np, axis=1)

    opt = float(inst.optimum_value)
    return dict(
        sigma=sigma, instance=inst.instance_id, seed=seed,
        best=y_obs,                                   # for the fidelity assertion
        regret_observed=opt - y_obs,
        regret_posterior=opt - y_post,
        regret_best_visited=opt - y_vis,
        dist_to_nearest_obs=float(dists.min()),
        argmax_is_new=bool(dists.min() > 1e-3),
        argmax_failed=failed,
    )


def by_instance(rows, key, insts=None):
    if insts is None:
        insts = sorted({r["instance"] for r in rows})
    return np.array([np.mean([r[key] for r in rows if r["instance"] == i])
                     for i in insts])


def report(rows) -> None:
    from scipy.stats import wilcoxon

    from boec.diagnostics import instance_bootstrap

    print("\n" + "=" * 96)
    print("PART A — RECOMMENDATION RULE, pure re-analysis of stored qLogEI runs at d=6")
    print("NOT REGISTERED. NOT A RESULT. No new evaluations; no configuration changed.")
    print("=" * 96)
    print(f"{'sigma':>6} {'rule':>26} {'median regret':>14} {'vs observed-best':>26} "
          f"{'p':>8}")
    for sigma in SIGMAS:
        sub = [r for r in rows if r["sigma"] == sigma]
        if not sub:
            continue
        o = by_instance(sub, "regret_observed")
        p_ = by_instance(sub, "regret_posterior")
        v = by_instance(sub, "regret_best_visited")
        print(f"{sigma:>6} {'observed-best (current)':>26} {np.median(o):>14.4f} "
              f"{'—':>26} {'—':>8}")
        d_ = p_ - o
        m, lo, hi = instance_bootstrap(d_, n_boot=2000)
        print(f"{sigma:>6} {'posterior argmax':>26} {np.median(p_):>14.4f} "
              f"{m:>+8.4f} [{lo:>+7.4f},{hi:>+7.4f}] {wilcoxon(d_).pvalue:>8.4f}")
        dv = v - o
        mv, lov, hiv = instance_bootstrap(dv, n_boot=2000)
        print(f"{sigma:>6} {'best VISITED (oracle bound)':>26} {np.median(v):>14.4f} "
              f"{mv:>+8.4f} [{lov:>+7.4f},{hiv:>+7.4f}] {wilcoxon(dv).pvalue:>8.4f}")
        # how much of the achievable recovery does the model's rule capture?
        recov = (np.mean(o) - np.mean(p_)) / max(np.mean(o) - np.mean(v), 1e-12)
        print(f"       -> the posterior rule recovers {100 * recov:5.1f}% of the gap "
              f"between what is reported and the best point BO actually visited")
        print(f"       -> posterior argmax is a point BO never evaluated in "
              f"{100 * np.mean([r['argmax_is_new'] for r in sub]):.0f}% of runs; "
              f"median distance to the nearest observation "
              f"{np.median([r['dist_to_nearest_obs'] for r in sub]):.4f}")
        nf = sum(r["argmax_failed"] for r in sub)
        if nf:
            print(f"       -> {nf} argmax optimisations FAILED and fell back to the "
                  f"observed best")
        print()

    print("  Reading it, per the pre-stated rule:")
    print("   * posterior materially better -> the reporting rule is costing BO real")
    print("     performance, and Part B follows.")
    print("   * no difference -> the model's accuracy does not translate into a better")
    print("     recommendation, i.e. it is accurate in the wrong places. Stop.")
    print("   * posterior worse -> the argmax lands where the GP is confidently wrong;")
    print("     that is a calibration finding and connects to E3's overconfidence.")
    print("  The sigma=0.10 row is the control: a noise-driven effect must SHRINK there.")


def main() -> None:
    grid = json.loads(Path("results/e2-grid.json").read_text())
    ref = {(r["sigma"], r["instance"], r["seed"]): r["best"] for r in grid
           if r["dim"] == DIM and r["arm"] == "qlogei"}

    tasks = [(sg, i, s) for sg in SIGMAS
             for i in range(N_INSTANCES) for s in range(N_SEEDS)]
    print(f"{len(tasks)} stored runs to regenerate and re-analyse", flush=True)
    rows = []
    with Pool(7) as pool:
        for k, r in enumerate(pool.imap_unordered(_row, tasks), 1):
            rows.append(r)
            if k % 25 == 0:
                print(f"  {k}/{len(tasks)}", flush=True)

    bad = [r for r in rows
           if abs(r["best"] - ref[(r["sigma"], r["instance"], r["seed"])]) > 1e-9]
    if bad:
        raise SystemExit(
            f"FIDELITY: {len(bad)}/{len(rows)} regenerated runs do not reproduce their "
            "stored E2 result. These are not the runs being re-analysed. Stop."
        )
    print(f"\nFIDELITY: {len(rows)}/{len(rows)} regenerated runs reproduce their stored "
          f"E2 `best` to 1e-9.")

    Path("results").mkdir(exist_ok=True)
    Path("results/exploratory-recommendation.json").write_text(json.dumps(rows, indent=1))
    report(rows)


if __name__ == "__main__":
    main()
