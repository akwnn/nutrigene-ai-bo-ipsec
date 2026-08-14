"""EXPLORATORY Part B — make the two arms structurally symmetric.

**NOT REGISTERED. NOT A RESULT. NOT AN ACQUISITION CHANGE.**

    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/exploratory_recommendation_b.py

Part A showed that recommending from the posterior mean instead of the best
observed value is worth -0.0320 regret at d=6/sigma=0.25 (p=0.0025) and accounts
for 54% of the DoE arm's margin. But Part A gave BO that recommendation for
FREE: the posterior argmax was a point BO had never evaluated in 100% of runs,
median distance 0.165 from its nearest observation, and no evaluation was spent
confirming it. The DoE arm spends one of its 48 on exactly that.

Part B pays for it. 47 adaptive evaluations, then the GP's posterior argmax is
EVALUATED as number 48 -- the same 47 + 1 structure the published pipeline uses.
Both arms now spend one evaluation confirming a model-based recommendation.

**This removes an asymmetry in how the answer is reported. It is not a change to
the acquisition function, the kernel, the budget or the design.** That
distinction is the whole difference between this and tuning, and it only holds
because the change is structural rather than chosen for its effect.

TWO SCORINGS, because E2 scores the DoE arm both ways (`e2.yaml` -> scoring ->
selected_point): its PRIMARY is `observed_argmax` and `confirmation_point` is
secondary. Reporting only one of them here would compare against whichever
happens to flatter BO.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import json                                      # noqa: E402
from multiprocessing import Pool                 # noqa: E402
from pathlib import Path                         # noqa: E402

import numpy as np                               # noqa: E402

DIM = 6
SIGMAS = (0.25, 0.10)
N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
N_SEARCH = 47                  # 47 adaptive + 1 confirmation, matching DoE's 20+27+1
N_RESTARTS = 20
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
                    CampaignConfig(d=DIM, budget=N_SEARCH, q=4, seed=seed,
                                   acq=AcqConfig(kind="qlogei"))).run()
    assert camp.train_X.shape[0] == N_SEARCH, camp.train_X.shape

    model = build_gp(camp.train_X, camp.train_Y, camp.train_Yvar, bounds)
    failed = False
    try:
        xh, _ = optimize_acqf(PosteriorMean(model), bounds=bounds, q=1,
                              num_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES)
    except Exception:                                        # noqa: BLE001
        failed = True
        obs = camp.train_Y.detach().double().cpu().numpy().ravel()
        xh = camp.train_X[int(np.argmax(obs))].unsqueeze(0)

    # SPEND evaluation 48 on the recommendation. This is the cost Part A avoided.
    Yc, Vc = orc.evaluate(xh)
    camp.tell(xh, Yc, Vc)
    assert camp.train_X.shape[0] == BUDGET, camp.train_X.shape

    opt = float(inst.optimum_value)
    # scoring 1 -- the pipeline's OUTPUT: truth at the confirmed recipe
    y_conf = float(orc.truth(xh).detach().double().cpu().numpy().ravel()[0])
    # scoring 2 -- E2's PRIMARY rule for the DoE arm: best observed over all 48,
    # scored at its true value. The confirmation point is a candidate like any other.
    y_obs48 = float(reported_best_curve(orc.truth(camp.train_X), camp.train_Y)[-1])

    Xn = camp.train_X[:N_SEARCH].detach().double().cpu().numpy()
    xh_np = xh.detach().double().cpu().numpy().ravel()
    return dict(
        sigma=sigma, instance=inst.instance_id, seed=seed,
        regret_confirmation=opt - y_conf,
        regret_observed48=opt - y_obs48,
        confirmation_underdelivered=bool(
            y_conf < float(reported_best_curve(orc.truth(camp.train_X[:N_SEARCH]),
                                               camp.train_Y[:N_SEARCH])[-1])),
        dist_to_nearest_obs=float(np.linalg.norm(Xn - xh_np, axis=1).min()),
        argmax_failed=failed,
    )


def by_instance(rows, key, ins=None):
    if ins is None:
        ins = sorted({r["instance"] for r in rows})
    return np.array([np.mean([r[key] for r in rows if r["instance"] == i]) for i in ins])


def report(rows, partA, grid) -> None:
    from scipy.stats import wilcoxon

    from boec.diagnostics import instance_bootstrap

    print("\n" + "=" * 98)
    print("PART B — 47 adaptive + 1 confirmation. Symmetric with the DoE pipeline.")
    print("NOT REGISTERED. NOT A RESULT. Not an acquisition change: only the way the")
    print("answer is produced changed, and one evaluation now pays for it.")
    print("=" * 98)

    for sigma in SIGMAS:
        sub = [r for r in rows if r["sigma"] == sigma]
        pa = [r for r in partA if r["sigma"] == sigma]
        doe = [r for r in grid if r["dim"] == DIM and r["sigma"] == sigma
               and r["arm"] == "doe"]
        e2 = [r for r in grid if r["dim"] == DIM and r["sigma"] == sigma
              and r["arm"] == "qlogei"]
        ins = sorted({r["instance"] for r in sub} & {r["instance"] for r in doe})

        b_conf = by_instance(sub, "regret_confirmation", ins)
        b_obs = by_instance(sub, "regret_observed48", ins)
        a_post = by_instance(pa, "regret_posterior", ins)
        a_obs = by_instance(pa, "regret_observed", ins)
        v_doe = by_instance(doe, "regret", ins)
        v_e2 = by_instance(e2, "regret", ins)

        print(f"\n  sigma_rel = {sigma}   (n={len(ins)} instances, paired)")
        print(f"    {'arm':>42} {'median regret':>14}")
        for lbl, v in (("E2 qLogEI, 48 search, observed-best", v_e2),
                       ("Part A: 48 search, posterior rec (FREE)", a_post),
                       ("Part B: 47 search + 1 confirmation", b_conf),
                       ("Part B, scored at best observed of 48", b_obs),
                       ("DoE arm (E2)", v_doe)):
            print(f"    {lbl:>42} {np.median(v):>14.4f}")

        print(f"\n    {'comparison':>42} {'difference':>26} {'p':>8}")
        for lbl, d_ in (
            ("Part B (confirm) vs E2 qLogEI", b_conf - v_e2),
            ("Part B (confirm) vs DoE", b_conf - v_doe),
            ("Part B (confirm) vs Part A free rec", b_conf - a_post),
            ("Part B (obs of 48) vs DoE", b_obs - v_doe),
        ):
            m, lo, hi = instance_bootstrap(d_, n_boot=2000)
            print(f"    {lbl:>42} {m:>+9.4f} [{lo:>+7.4f},{hi:>+7.4f}] "
                  f"{wilcoxon(d_).pvalue:>8.4f}")

        gap0 = float(np.mean(a_obs - v_doe))
        gapB = float(np.mean(b_conf - v_doe))
        # only meaningful when there IS a gap: at sigma=0.10 the E2 arms are tied
        # (-0.0018), so a percentage of it is a division by approximately zero and
        # prints nonsense like "-844% closed". Reported as absolute change instead.
        if abs(gap0) > 0.01:
            print(f"\n    -> of the E2 gap to DoE ({gap0:+.4f}), Part B closes "
                  f"{100 * (gap0 - gapB) / gap0:.0f}%; {100 * gapB / gap0:.0f}% remains")
        else:
            print(f"\n    -> E2 had these arms TIED here ({gap0:+.4f}), so no "
                  f"percentage of the gap is meaningful. Absolute change: "
                  f"{gap0:+.4f} -> {gapB:+.4f}")
        cost = float(np.mean(b_conf - a_post))
        print(f"    -> the confirmation run COSTS {cost:+.4f} against Part A's free "
              f"recommendation")
        print(f"    -> the confirmed recipe under-delivers against the arm's own best "
              f"observation in {100 * np.mean([r['confirmation_underdelivered'] for r in sub]):.0f}% "
              f"of runs")
        print(f"    -> median distance from the confirmed point to its nearest "
              f"observation: {np.median([r['dist_to_nearest_obs'] for r in sub]):.4f}")
        nf = sum(r["argmax_failed"] for r in sub)
        if nf:
            print(f"    -> {nf} argmax optimisations FAILED and fell back to observed best")

    print("\n  The DoE arm's own confirmation under-delivers in 100% of runs "
          "(results/doe-arm.log).")
    print("  Whether BO's does too is the like-for-like question, and it is above.")


def main() -> None:
    grid = json.loads(Path("results/e2-grid.json").read_text())
    partA = json.loads(Path("results/exploratory-recommendation.json").read_text())

    tasks = [(sg, i, s) for sg in SIGMAS
             for i in range(N_INSTANCES) for s in range(N_SEEDS)]
    print(f"{len(tasks)} campaigns at 47 search + 1 confirmation", flush=True)
    rows = []
    with Pool(7) as pool:
        for k, r in enumerate(pool.imap_unordered(_row, tasks), 1):
            rows.append(r)
            if k % 25 == 0:
                print(f"  {k}/{len(tasks)}", flush=True)

    Path("results/exploratory-recommendation-b.json").write_text(json.dumps(rows, indent=1))
    report(rows, partA, grid)


if __name__ == "__main__":
    main()
