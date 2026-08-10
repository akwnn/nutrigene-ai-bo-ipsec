"""Q26 — does the opening batch SIZE explain the d=6 blindness?

OWNERSHIP: Person A. **DIAGNOSTIC. E2 IS UNCHANGED AND STAYS UNCHANGED.**
The pre-registered primary keeps `n_init = 2d+2 = 14` at d=6 whatever this returns.

Run with::

    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/confound_ninit.py

Pre-registered in `docs/OPEN-QUESTIONS.md` Q26, committed before the first run.
Check this file's git timestamp against that entry's.

------------------------------------------------------------------------------
THE ONE VARIABLE
------------------------------------------------------------------------------

Q25 found the surrogate at d=6 is indistinguishable from a fit to permuted
outcomes at the moment adaptive search begins, while at d=8 it is not. Three
things differ between those cells: opening size (14 vs 18), dimension (6 vs 8),
and the influence of each individual inert factor (0.10/2 = 0.050 vs
0.10/4 = 0.025). This moves ONLY the first.

The manipulation is exactly nested. `sobol_design(bounds, 18, seed)[:14]` is
bit-identical to `initial_design(bounds, seed)`, asserted in the suite, so the
treatment is "the same fourteen points, plus four more" and cannot be confounded
with a change of design.

PRIMARY endpoint: ARD separation (inert / active fitted lengthscale) on the
OPENING DESIGN, against a paired permuted-outcome null. Not regret -- the claim
is about what the model knows when adaptive search starts.

SECONDARY, marked as such throughout: simple regret at budget 48 under the
larger opening. This is NOT a corrected E2 result. At n_init=18 there are 30
adaptive evaluations instead of 34, and if separation improves while regret does
not, the seed round bought knowledge and spent the budget that would have used
it -- which is the more interesting outcome, not a null.
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
N_INITS = (14, 18)          # 14 = the pre-registered rule; 18 = d=8's opening
N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
N_PERM = 3
FINAL = 46                  # a real round boundary under both openings


def _opening(task) -> dict:
    """PRIMARY. Opening-design ARD separation vs its own permutation null."""
    import torch

    torch.set_num_threads(1)

    from boec.lengthscale_diag import permutation_null_lengthscales
    from boec.optimizers import sobol_design
    from boec.oracles import load_ensemble
    from boec.surrogate import build_gp, lengthscales
    from boec.torch_oracle import BiphasicOracle

    sigma, i_inst, seed, n_init = task
    inst = load_ensemble(dim=DIM)[i_inst]
    mask = np.asarray(inst.active_mask, dtype=bool)
    bounds = torch.stack([torch.zeros(DIM, dtype=torch.double),
                          torch.ones(DIM, dtype=torch.double)])

    X = sobol_design(bounds, n_init, seed=seed)
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    Y, V = orc.evaluate(X)

    ls = lengthscales(build_gp(X, Y, V, bounds)).detach().double().cpu().numpy().ravel()
    null = permutation_null_lengthscales(X, Y, V, bounds, n_perm=N_PERM, seed=seed)
    return dict(
        sigma=sigma, instance=inst.instance_id, seed=seed, n_init=n_init,
        fit_ratio=float(np.median(ls[~mask]) / np.median(ls[mask])),
        null_ratio=float(np.median(
            [np.median(r[~mask]) / np.median(r[mask]) for r in null])),
        ls_active=float(np.median(ls[mask])),
        ls_inert=float(np.median(ls[~mask])),
    )


def _campaign(task) -> dict:
    """SECONDARY. Full campaign at the larger opening. Not a corrected E2 run."""
    import torch

    torch.set_num_threads(1)

    from boec.campaign import Campaign, CampaignConfig
    from boec.diagnostics import reported_best_curve
    from boec.lengthscale_diag import permutation_null_lengthscales
    from boec.optimizers import AcqConfig
    from boec.oracles import load_ensemble
    from boec.surrogate import build_gp, lengthscales
    from boec.torch_oracle import BiphasicOracle

    sigma, i_inst, seed, n_init = task
    inst = load_ensemble(dim=DIM)[i_inst]
    mask = np.asarray(inst.active_mask, dtype=bool)
    bounds = torch.stack([torch.zeros(DIM, dtype=torch.double),
                          torch.ones(DIM, dtype=torch.double)])

    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cfg = CampaignConfig(d=DIM, budget=BUDGET, q=4, seed=seed, n_init=n_init,
                         acq=AcqConfig(kind="qlogei"))
    camp = Campaign(orc, bounds, cfg).run()
    assert camp.train_X.shape[0] == BUDGET, camp.train_X.shape

    best = float(reported_best_curve(orc.truth(camp.train_X), camp.train_Y)[-1])
    ls = lengthscales(
        build_gp(camp.train_X[:FINAL], camp.train_Y[:FINAL],
                 camp.train_Yvar[:FINAL], bounds)
    ).detach().double().cpu().numpy().ravel()
    null = permutation_null_lengthscales(
        camp.train_X[:FINAL], camp.train_Y[:FINAL], camp.train_Yvar[:FINAL],
        bounds, n_perm=N_PERM, seed=seed)
    return dict(
        sigma=sigma, instance=inst.instance_id, seed=seed, n_init=n_init,
        best=best, regret=float(inst.optimum_value - best),
        n_adaptive=BUDGET - n_init,
        final_fit_ratio=float(np.median(ls[~mask]) / np.median(ls[mask])),
        final_null_ratio=float(np.median(
            [np.median(r[~mask]) / np.median(r[mask]) for r in null])),
    )


def _d8_reference() -> dict:
    """d=8's opening separation, recomputed under THIS script's estimator.

    Q26 registered 1.150 and 1.718 as the values to beat. Those came from Q25's
    report, which aggregated over all 50 RUNS; this script clusters on the 25
    instances and works in log space. Same underlying per-run ratios, different
    aggregation, and the difference is not a constant offset -- so quoting the
    old numbers beside this table would compare two scales. Recomputed here from
    the committed Q25 rows, with no refitting.
    """
    f = Path("results/diagnostic-lengthscales.json")
    if not f.exists():
        return {}
    rows = json.loads(f.read_text())
    out = {}
    for sigma in SIGMAS:
        sub = [r for r in rows if r["dim"] == 8 and r["sigma"] == sigma]
        if not sub:
            continue
        insts = sorted({r["instance"] for r in sub})
        v = [np.mean([np.log(np.median(r["checkpoints"]["init"]["ls_inert"]) /
                             np.median(r["checkpoints"]["init"]["ls_active"]))
                      for r in sub if r["instance"] == i]) for i in insts]
        out[sigma] = float(np.exp(np.median(v)))
    return out


def _by_instance(rows, key, log=False):
    """Cluster on instance: E2's rule is n=25 landscapes, not 50 runs.

    `log=True` for ratio-valued keys. A signed-RANK test needs the paired
    differences to be symmetric under the null, and a difference of two ratios
    is right-skewed -- measured type-I error on this pipeline is 8.9% at a
    nominal 5% and 2.0% at a nominal 1%. On the log scale it is 4.9% and 0.9%,
    i.e. nominal. Ratios are compared in log space throughout; medians are
    exponentiated back only for display.
    """
    insts = sorted({r["instance"] for r in rows})
    f = (lambda v: np.log(v)) if log else (lambda v: v)
    return np.array([np.mean([f(r[key]) for r in rows if r["instance"] == i])
                     for i in insts])


def report(op: list[dict], camp: list[dict], e2: dict) -> None:
    from scipy.stats import wilcoxon

    def sel(rows, sigma, n_init):
        return [r for r in rows if r["sigma"] == sigma and r["n_init"] == n_init]

    print("\n" + "=" * 92)
    print("PRIMARY — ARD separation on the OPENING DESIGN, d=6, vs a permuted-outcome null")
    print("=" * 92)
    print("Pre-registered prediction: sigma=0.25 will NOT discriminate (p>0.05);")
    print("                           sigma=0.10 WILL (p<0.01).")
    ref = _d8_reference()
    if ref:
        print(f"Reference, d=8 at the SAME opening size of 18, recomputed under THIS "
              f"script's estimator")
        print(f"(instance-clustered, log scale): sigma=0.25 {ref[0.25]:.3f}, "
              f"sigma=0.10 {ref[0.10]:.3f}.")
        print("Q26 registered 1.150 / 1.718 for these. Those were Q25's run-level "
              "figures and are")
        print("NOT on this table's scale -- see the correction note in Q26.\n")
    print(f"{'sigma':>6} {'n_init':>7} {'fit':>22} {'null':>22} {'p(fit>null)':>12} "
          f"{'verdict':>14}")
    verdicts = {}
    for sigma in SIGMAS:
        for n_init in N_INITS:
            sub = sel(op, sigma, n_init)
            f = np.exp(_by_instance(sub, "fit_ratio", log=True))
            n = np.exp(_by_instance(sub, "null_ratio", log=True))
            p = wilcoxon(_by_instance(sub, "fit_ratio", log=True)
                         - _by_instance(sub, "null_ratio", log=True),
                         alternative="greater").pvalue
            v = ("DISCRIMINATES" if p < 0.01 else
                 "ambiguous" if p < 0.05 else "no")
            verdicts[(sigma, n_init)] = (float(np.median(f)), float(p), v)
            print(f"{sigma:>6} {n_init:>7} "
                  f"{np.median(f):>8.3f} [{np.percentile(f, 25):>5.3f},"
                  f"{np.percentile(f, 75):>6.3f}] "
                  f"{np.median(n):>8.3f} [{np.percentile(n, 25):>5.3f},"
                  f"{np.percentile(n, 75):>6.3f}] "
                  f"{p:>12.2e} {v:>14}")

    print("\n  PAIRED, same instances and seeds — 18 points against the same 14 plus four.")
    print("  Reported as a DIFFERENCE IN DIFFERENCES: each arm against its OWN null, then")
    print("  differenced. A plain 14->18 comparison is anchored at zero, but the null")
    print("  itself moves with n, so the anchor has to move with it.")
    for sigma in SIGMAS:
        a = sel(op, sigma, 14)
        b = sel(op, sigma, 18)
        ea = _by_instance(a, "fit_ratio", log=True) - _by_instance(a, "null_ratio", log=True)
        eb = _by_instance(b, "fit_ratio", log=True) - _by_instance(b, "null_ratio", log=True)
        p = wilcoxon(eb - ea, alternative="greater").pvalue
        print(f"    sigma={sigma}: excess over null "
              f"{np.exp(np.mean(ea)):.3f}x -> {np.exp(np.mean(eb)):.3f}x   "
              f"DiD {np.exp(np.mean(eb - ea)):.3f}x   wilcoxon p={p:.4f}")

    print("\n" + "=" * 92)
    print("SECONDARY — regret at budget 48. NOT A CORRECTED E2 RESULT.")
    print("=" * 92)
    print(f"{'sigma':>6} {'arm':>26} {'n_adaptive':>11} {'median regret':>14} "
          f"{'vs n_init=14':>26} {'p':>9}")
    for sigma in SIGMAS:
        base_arr = None
        for n_init in sorted(N_INITS):
            sub = sel(camp, sigma, n_init)
            if not sub:
                continue
            r = _by_instance(sub, "regret")
            if n_init == 14:
                print(f"{sigma:>6} {'qlogei n_init=14 (E2)':>26} {BUDGET - 14:>11} "
                      f"{np.median(r):>14.4f} {'—':>26} {'—':>9}")
                base_arr = r
            elif base_arr is None:
                print(f"{sigma:>6} {'qlogei n_init=18':>26} {BUDGET - 18:>11} "
                      f"{np.median(r):>14.4f} {'no n_init=14 baseline in run':>26} "
                      f"{'—':>9}")
                continue
            else:
                d = r - base_arr
                p = wilcoxon(d).pvalue
                print(f"{sigma:>6} {'qlogei n_init=18':>26} {BUDGET - 18:>11} "
                      f"{np.median(r):>14.4f} "
                      f"{np.mean(d):>+10.4f} (>0 = worse) {p:>9.4f}")
        # registered in Q26 and previously printed untested, which Q24 warns is
        # read as a comparison whatever the caption says. Now it IS the comparison.
        doe = e2[(sigma, "doe")]
        sub18 = sel(camp, sigma, 18)
        if len(doe) == len(sub18) // N_SEEDS:
            r18 = _by_instance(sub18, "regret")
            dd = r18 - doe
            print(f"{sigma:>6} {'doe (E2)':>26} {'—':>11} {np.median(doe):>14.4f} "
                  f"{np.mean(dd):>+10.4f} (n=18 vs doe) {wilcoxon(dd).pvalue:>9.4f}")

    print("\n" + "=" * 92)
    print("SECONDARY — final-stage ARD separation at n=46, to confirm the noise pattern")
    print("=" * 92)
    for sigma in SIGMAS:
        for n_init in N_INITS:
            sub = sel(camp, sigma, n_init)
            if not sub:
                continue
            f = _by_instance(sub, "final_fit_ratio")
            n = _by_instance(sub, "final_null_ratio")
            print(f"  sigma={sigma} n_init={n_init}: fit {np.median(f):.3f}  "
                  f"null {np.median(n):.3f}")

    print("\n" + "=" * 92)
    print("WHAT THIS CANNOT SETTLE")
    print("=" * 92)
    print("  Per-factor inertness is untouched: each inert factor carries 0.050 of the")
    print("  weight at d=6 and 0.025 at d=8, so every individual nuisance factor at d=8")
    print("  is half as influential and correspondingly easier to identify as inert.")
    print("  ONE CONFOUND OF THREE. This is not 'we isolated the mechanism'.")


def main() -> None:
    # stored E2 reference, for the secondary comparison only
    grid = json.loads(Path("results/e2-grid.json").read_text())
    e2 = {}
    for sigma in SIGMAS:
        for arm in ("qlogei", "doe"):
            rows = [r for r in grid
                    if r["dim"] == DIM and r["sigma"] == sigma and r["arm"] == arm]
            e2[(sigma, arm)] = _by_instance(rows, "regret") if rows else np.array([])

    tasks = [(sg, i, s, n)
             for sg in SIGMAS for i in range(N_INSTANCES)
             for s in range(N_SEEDS) for n in N_INITS]

    print(f"PRIMARY: {len(tasks)} opening-design fits", flush=True)
    with Pool(7) as pool:
        op = list(pool.imap_unordered(_opening, tasks))

    # FIDELITY on the baseline arm: the n_init=14 campaigns must still reproduce
    # the stored E2 rows, or the comparison is against a different experiment.
    ref = {(r["sigma"], r["instance"], r["seed"]): r["best"]
           for r in grid if r["dim"] == DIM and r["arm"] == "qlogei"}
    print(f"SECONDARY: {len(tasks)} campaigns", flush=True)
    with Pool(7) as pool:
        camp = []
        for k, r in enumerate(pool.imap_unordered(_campaign, tasks), 1):
            camp.append(r)
            if k % 25 == 0:
                print(f"  {k}/{len(tasks)}", flush=True)

    bad = [r for r in camp if r["n_init"] == 14
           and abs(r["best"] - ref[(r["sigma"], r["instance"], r["seed"])]) > 1e-9]
    if bad:
        raise SystemExit(
            f"FIDELITY: {len(bad)} n_init=14 campaigns do not reproduce their stored "
            "E2 result. The baseline is not E2 and nothing below is comparable to it."
        )
    n14 = sum(1 for r in camp if r["n_init"] == 14)
    print(f"\nFIDELITY: {n14}/{n14} n_init=14 campaigns reproduce their stored E2 "
          f"`best` to 1e-9.")

    Path("results").mkdir(exist_ok=True)
    Path("results/confound-ninit.json").write_text(
        json.dumps({"opening": op, "campaign": camp}, indent=1))
    report(op, camp, e2)


if __name__ == "__main__":
    main()
