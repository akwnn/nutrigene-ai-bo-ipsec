"""EXPLORATORY — three modifications, independently and jointly. See EXPLORATORY.md.

**NOT REGISTERED. NOT A RESULT. NOT A REVISION TO E2.**

    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/exploratory_three_factor.py

Full 2^3 factorial at d=6, sigma_rel=0.25 -- the cell where BO loses -- over the
same 25 instances x 2 seeds, paired throughout.

  mean : ConstantMean            vs a full second-order trend (universal kriging)
  rep  : 1 evaluation/condition  vs 2, at a FIXED 48-evaluation budget
  warp : none                    vs a Kumaraswamy input warp

Cell 1 is the pre-registered configuration and is ASSERTED to reproduce its
stored E2 numbers. If it does not, the harness moved and nothing else is valid.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import itertools                                 # noqa: E402
import json                                      # noqa: E402
from multiprocessing import Pool                 # noqa: E402
from pathlib import Path                         # noqa: E402

import numpy as np                               # noqa: E402

DIM = 6
SIGMA = 0.25
N_INSTANCES = 25
N_SEEDS = 2
BUDGET_EVALS = 48
N_PERM = 3
DOE_REFERENCE = 0.0934          # E2's DoE arm, instance-clustered median

CELLS = [dict(mean=m, rep=r, warp=w)
         for m, r, w in itertools.product(("const", "quad"), (1, 2), (False, True))]


def cell_name(c) -> str:
    return f"{c['mean']}/r{c['rep']}/{'warp' if c['warp'] else 'nowarp'}"


def _build(cfg, X, Y, V, bounds):
    from boec.exploratory import QuadraticMean
    from boec.surrogate import build_gp
    mm = QuadraticMean(d=int(X.shape[-1])) if cfg["mean"] == "quad" else None
    return build_gp(X, Y, V, bounds, mean_module=mm, warp=cfg["warp"])


def _run(task) -> dict:
    try:
        return _run_inner(task)
    except Exception as exc:                       # noqa: BLE001
        # Recorded, never silently dropped: quad+warp+replication produces NaN
        # gradients in `optimize_acqf`. A cell that fails on some instances and
        # succeeds on others would otherwise be scored on the subset where it
        # happened to converge, which flatters it.
        ci, i_inst, seed, dim, sigma = task
        return dict(cell=ci, cell_name=cell_name(CELLS[ci]), dim=dim, sigma=sigma,
                    instance=f"FAILED-{i_inst}", seed=seed, failed=True,
                    error=f"{type(exc).__name__}: {str(exc)[:160]}")


def _run_inner(task) -> dict:
    import torch

    torch.set_num_threads(1)

    from boec.campaign import Campaign, CampaignConfig
    from boec.diagnostics import reported_best_curve
    from boec.exploratory import ReplicatedEvaluator, replicated_plan
    from boec.optimizers import AcqConfig, sobol_design
    from boec.oracles import load_ensemble
    from boec.rsm import fit_second_order, second_order_n_terms
    from boec.surrogate import lengthscales, predictive
    from boec.torch_oracle import BiphasicOracle

    ci, i_inst, seed, dim, sigma = task
    cfg = CELLS[ci]
    inst = load_ensemble(dim=dim)[i_inst]
    mask = np.asarray(inst.active_mask, dtype=bool)
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])

    n_cond, n_init, q = replicated_plan(BUDGET_EVALS, cfg["rep"], dim)

    class _Camp(Campaign):
        """Only `fit` differs from the shared class, so cell 1 is bit-identical."""

        def fit(self):
            return _build(cfg, self.train_X, self.train_Y, self.train_Yvar, self.bounds)

    base = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    ev = ReplicatedEvaluator(base, r=cfg["rep"]) if cfg["rep"] > 1 else base
    camp = _Camp(ev, bounds,
                 CampaignConfig(d=dim, budget=n_cond, q=q, seed=seed,
                                n_init=(None if cfg["rep"] == 1 else n_init),
                                acq=AcqConfig(kind="qlogei")))
    camp.run()

    spent = (ev.n_evaluations if cfg["rep"] > 1
             else int(camp.train_X.shape[0]))
    assert spent == BUDGET_EVALS, (cell_name(cfg), spent)

    best = float(reported_best_curve(base.truth(camp.train_X), camp.train_Y)[-1])
    out = dict(cell=ci, cell_name=cell_name(cfg), dim=dim, sigma=sigma,
               instance=inst.instance_id, seed=seed, n_evaluations=spent,
               n_conditions=int(camp.train_X.shape[0]),
               best=best, regret=float(inst.optimum_value - best))

    # --- opening-design ARD separation, with a null recomputed FOR THIS CELL --
    # a null computed once and reused would answer a different question in seven
    # of the eight cells: warping changes the input space, and a quadratic trend
    # changes what the kernel is left to explain
    n_open = camp.train_X.shape[0] if False else (2 * dim + 2 if cfg["rep"] == 1
                                                  else n_init)
    Xo = sobol_design(bounds, n_open, seed=seed)
    Yo, Vo = (ReplicatedEvaluator(BiphasicOracle(inst, sigma_rel=sigma, seed=seed),
                                  r=cfg["rep"]).evaluate(Xo) if cfg["rep"] > 1
              else BiphasicOracle(inst, sigma_rel=sigma, seed=seed).evaluate(Xo))
    ls = lengthscales(_build(cfg, Xo, Yo, Vo, bounds)
                      ).detach().double().cpu().numpy().ravel()
    rng = np.random.default_rng(1000 * seed + i_inst)      # per-instance, not per-cell
    nulls = []
    for _ in range(N_PERM):
        idx = torch.as_tensor(rng.permutation(int(Yo.shape[0])), dtype=torch.long)
        nl = lengthscales(_build(cfg, Xo, Yo[idx], Vo[idx], bounds)
                          ).detach().double().cpu().numpy().ravel()
        nulls.append(float(np.median(nl[~mask]) / np.median(nl[mask])))
    out["open_fit_ratio"] = float(np.median(ls[~mask]) / np.median(ls[mask]))
    out["open_null_ratio"] = float(np.median(nulls))
    # GUARD the brief asked for: does ARD separation still MEAN anything here?
    # Under a quadratic trend the kernel is left with nothing dimension-specific
    # to explain and every lengthscale stays at its initialisation (the prior
    # mode, 0.5016), so the ratio is 1.000 BY CONSTRUCTION for both the fit and
    # the null. Flagged per run so the report can refuse to quote the metric
    # rather than quoting a number that cannot discriminate.
    from boec.lengthscale_diag import prior_mode
    pm = prior_mode(_build(cfg, Xo, Yo, Vo, bounds))
    out["ard_at_initialisation"] = bool(np.allclose(ls, pm, rtol=5e-3))

    # --- is the GP contributing anything under a quadratic mean? --------------
    # compared against a pure OLS second-order fit on the SAME data. Close
    # agreement means the polynomial's model was simply the right one, which is
    # a stronger finding than "BO can be improved".
    n_fit = int(camp.train_X.shape[0])
    if n_fit > second_order_n_terms(dim):
        poly = fit_second_order(camp.train_X, camp.train_Y)
        Xt = sobol_design(bounds, 256, seed=9999)
        gp_mu = predictive(camp.fit(), Xt).mean.detach().double().cpu().numpy().ravel()
        po_mu = poly.predict(Xt).detach().double().cpu().numpy().ravel()
        tr = base.truth(Xt).detach().double().cpu().numpy().ravel()
        out["gp_poly_corr"] = float(np.corrcoef(gp_mu, po_mu)[0, 1])
        out["gp_poly_rms"] = float(np.sqrt(np.mean((gp_mu - po_mu) ** 2)))
        out["gp_rms_vs_truth"] = float(np.sqrt(np.mean((gp_mu - tr) ** 2)))
        out["poly_rms_vs_truth"] = float(np.sqrt(np.mean((po_mu - tr) ** 2)))
    return out


def by_instance(rows, key, log=False, insts=None):
    if insts is None:
        insts = sorted({r["instance"] for r in rows})
    f = np.log if log else (lambda v: v)
    return np.array([np.mean([f(r[key]) for r in rows if r["instance"] == i])
                     for i in insts])


def paired(a_rows, b_rows, key, log=False):
    """Pair on the INSTANCES both arms actually completed.

    Cell 8 (quad/r2/warp) fails on 36 of 50 runs, leaving 11 instances against
    the baseline's 25. Differencing without intersecting would either crash or,
    worse, silently compare different landscape sets -- and the surviving subset
    is exactly the one where that configuration happened to converge, which
    flatters it. The comparison is therefore made on the common set and the
    shrunken n is printed beside it.
    """
    common = sorted({r["instance"] for r in a_rows} & {r["instance"] for r in b_rows})
    return (by_instance(a_rows, key, log, common),
            by_instance(b_rows, key, log, common), len(common))


def report(rows) -> None:
    from scipy.stats import wilcoxon

    from boec.diagnostics import instance_bootstrap

    def sel(ci, dim=DIM, sigma=SIGMA):
        return [r for r in rows if r["cell"] == ci and r["dim"] == dim
                and r["sigma"] == sigma and not r.get("failed")]

    def n_failed(ci, dim=DIM, sigma=SIGMA):
        return sum(1 for r in rows if r["cell"] == ci and r["dim"] == dim
                   and r["sigma"] == sigma and r.get("failed"))

    def ard_dead(ci):
        s_ = sel(ci)
        return bool(s_) and np.mean([r.get("ard_at_initialisation", False)
                                     for r in s_]) > 0.5

    print("\n" + "=" * 100)
    print("EXPLORATORY 2^3 FACTORIAL — d=6, sigma=0.25.  NOT REGISTERED, NOT A RESULT.")
    print("=" * 100)
    print(f"{'#':>2} {'cell':>22} {'regret (median)':>16} {'vs cell 1':>24} {'p':>8} "
          f"{'ARD open':>9} {'null':>7} {'p':>8}")
    base = by_instance(sel(0), "regret")
    for ci, c in enumerate(CELLS):
        sub = sel(ci)
        if not sub:
            continue
        r = by_instance(sub, "regret")
        if ard_dead(ci):
            ards = f"{'DEAD':>9} {'—':>7} {'—':>8}"
        else:
            f = by_instance(sub, "open_fit_ratio", log=True)
            n = by_instance(sub, "open_null_ratio", log=True)
            pa = wilcoxon(f - n, alternative="greater").pvalue
            ards = (f"{np.exp(np.median(f)):>9.3f} {np.exp(np.median(n)):>7.3f} "
                    f"{pa:>8.4f}")
        fail = f"  [{n_failed(ci)} failed]" if n_failed(ci) else ""
        if ci == 0:
            print(f"{ci + 1:>2} {cell_name(c):>22} {np.median(r):>16.4f} "
                  f"{'baseline':>24} {'—':>8} {ards}{fail}")
            continue
        b0, b1, n_common = paired(sel(0), sub, "regret")
        d_ = b1 - b0
        m, lo, hi = instance_bootstrap(d_, n_boot=2000)
        nstar = "" if n_common == N_INSTANCES else f"  [n={n_common}]"
        print(f"{ci + 1:>2} {cell_name(c):>22} {np.median(r):>16.4f} "
              f"{m:>+8.4f} [{lo:>+7.4f},{hi:>+7.4f}] {wilcoxon(d_).pvalue:>8.4f} "
              f"{ards}{fail}{nstar}")
    print("\n  'vs cell 1' is the change in regret; NEGATIVE = better than the "
          "pre-registered config.")
    print("  ARD 'DEAD' = the metric cannot discriminate in that cell. Under a")
    print("  quadratic trend the kernel has nothing dimension-specific left to")
    print("  explain, so every lengthscale stays at its initialisation (0.5016, the")
    print("  prior mode) and the ratio is 1.000 BY CONSTRUCTION for fit and null")
    print("  alike. Reported as undefined rather than as a number. That degeneracy")
    print("  is itself the most direct evidence that the trend, not the kernel, is")
    print("  doing the modelling.")
    print(f"  DoE reference (E2, instance-clustered median): {DOE_REFERENCE:.4f}")

    print("\n" + "=" * 100)
    print("MAIN EFFECTS — each factor averaged over the other two, paired by instance")
    print("=" * 100)
    for factor, lo_v, hi_v in (("mean", "const", "quad"), ("rep", 1, 2),
                               ("warp", False, True)):
        for metric, log in (("regret", False), ("open_fit_ratio", True)):
            a = [r for r in rows if r["dim"] == DIM and r["sigma"] == SIGMA
                 and not r.get("failed") and CELLS[r["cell"]][factor] == lo_v]
            b = [r for r in rows if r["dim"] == DIM and r["sigma"] == SIGMA
                 and not r.get("failed") and CELLS[r["cell"]][factor] == hi_v]
            if not a or not b:
                continue
            va, vb, _n = paired(a, b, metric, log)
            d_ = vb - va
            p = wilcoxon(d_).pvalue
            unit = "x" if log else ""
            shown = (f"{np.exp(np.mean(va)):.3f} -> {np.exp(np.mean(vb)):.3f}" if log
                     else f"{np.mean(va):.4f} -> {np.mean(vb):.4f}")
            print(f"  {factor:>5} {str(lo_v):>5} -> {str(hi_v):<5} {metric:>15}: "
                  f"{shown:>20}{unit}  mean diff {np.mean(d_):>+8.4f}  p={p:.4f}")

    print("\n" + "=" * 100)
    print("INTERACTIONS on regret (paired by instance)")
    print("=" * 100)
    def cells_where(**kw):
        return [r for r in rows if r["dim"] == DIM and r["sigma"] == SIGMA
                and not r.get("failed")
                and all(CELLS[r["cell"]][k] == v for k, v in kw.items())]
    for f1, v1a, v1b in (("mean", "const", "quad"),):
        for f2, v2a, v2b in (("rep", 1, 2), ("warp", False, True)):
            groups = {(x, y): cells_where(**{f1: x, f2: y})
                      for x, y in itertools.product((v1a, v1b), (v2a, v2b))}
            if any(not v for v in groups.values()):
                continue
            common = set.intersection(*[{r["instance"] for r in v}
                                        for v in groups.values()])
            common = sorted(common)
            g = {k: by_instance(v, "regret", insts=common)
                 for k, v in groups.items()}
            inter = (g[(v1b, v2b)] - g[(v1a, v2b)]) - (g[(v1b, v2a)] - g[(v1a, v2a)])
            print(f"  {f1} x {f2} (n={len(common)}): interaction {np.mean(inter):>+8.4f}  "
                  f"p={wilcoxon(inter).pvalue:.4f}   "
                  f"(effect of {f1} at {f2}={v2a}: "
                  f"{np.mean(g[(v1b, v2a)] - g[(v1a, v2a)]):+.4f}; at {f2}={v2b}: "
                  f"{np.mean(g[(v1b, v2b)] - g[(v1a, v2b)]):+.4f})")

    print("\n" + "=" * 100)
    print("IS THE GP CONTRIBUTING ANYTHING?  GP posterior mean vs an OLS second-order")
    print("fit on the SAME data. High agreement => the polynomial's model was the right")
    print("one, which is a stronger finding than 'BO can be improved'.")
    print("=" * 100)
    print(f"{'cell':>22} {'corr(GP, poly)':>15} {'RMS |GP-poly|':>14} "
          f"{'GP RMS vs truth':>16} {'poly RMS vs truth':>18}")
    for ci, c in enumerate(CELLS):
        sub = [r for r in sel(ci) if "gp_poly_corr" in r]
        if not sub:
            print(f"{cell_name(c):>22} {'n/a — 24 conditions < 28 terms':>65}")
            continue
        print(f"{cell_name(c):>22} "
              f"{np.median([r['gp_poly_corr'] for r in sub]):>15.4f} "
              f"{np.median([r['gp_poly_rms'] for r in sub]):>14.4f} "
              f"{np.median([r['gp_rms_vs_truth'] for r in sub]):>16.4f} "
              f"{np.median([r['poly_rms_vs_truth'] for r in sub]):>18.4f}")

    print("\n" + "=" * 100)
    print("BEST CELL vs DoE — SELECTED ON THE OUTCOME, SO THIS ESTIMATE IS INFLATED")
    print("=" * 100)
    meds = {ci: float(np.median(by_instance(sel(ci), "regret")))
            for ci in range(len(CELLS)) if sel(ci)}
    best = min(meds, key=meds.get)
    print(f"  best of {len(meds)} cells: #{best + 1} {cell_name(CELLS[best])} at "
          f"{meds[best]:.4f}, against DoE's {DOE_REFERENCE:.4f}")
    print("  The best of eight configurations, chosen after seeing the outcome, is not")
    print("  an unbiased estimate of anything. If this becomes a claim it must be")
    print("  re-run on fresh instances under a registration written first.")

    for dim, sigma, label in ((DIM, 0.10, "sigma=0.10 — does it survive where BO ties?"),
                              (8, 0.25, "d=8 — does it break what already works?")):
        sub = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma]
        if not sub:
            continue
        print(f"\n  OUT-OF-CELL CHECK, {label}")
        for ci in sorted({r["cell"] for r in sub}):
            s = [r for r in sub if r["cell"] == ci]
            print(f"    {cell_name(CELLS[ci]):>22}: regret "
                  f"{np.median(by_instance(s, 'regret')):.4f}")


def main() -> None:
    grid = json.loads(Path("results/e2-grid.json").read_text())
    ref = {(r["instance"], r["seed"]): r["best"] for r in grid
           if r["dim"] == DIM and r["sigma"] == SIGMA and r["arm"] == "qlogei"}

    tasks = [(ci, i, s, DIM, SIGMA)
             for ci in range(len(CELLS))
             for i in range(N_INSTANCES) for s in range(N_SEEDS)]
    print(f"{len(tasks)} campaigns across {len(CELLS)} cells", flush=True)
    rows = []
    with Pool(7) as pool:
        for k, r in enumerate(pool.imap_unordered(_run, tasks), 1):
            rows.append(r)
            if k % 50 == 0:
                print(f"  {k}/{len(tasks)}", flush=True)

    rows_ok = [r for r in rows if not r.get("failed")]
    nf = len(rows) - len(rows_ok)
    if nf:
        print(f"\n{nf}/{len(rows)} runs FAILED and are excluded (recorded in the json):")
        for ci in range(len(CELLS)):
            k = sum(1 for r in rows if r["cell"] == ci and r.get("failed"))
            if k:
                ex = next(r["error"] for r in rows if r["cell"] == ci and r.get("failed"))
                print(f"  {cell_name(CELLS[ci]):>22}: {k} — {ex}")
    bad = [r for r in rows if r["cell"] == 0 and not r.get("failed")
           and abs(r["best"] - ref[(r["instance"], r["seed"])]) > 1e-9]
    if bad:
        raise SystemExit(
            f"CELL 1 DOES NOT REPRODUCE E2 in {len(bad)} runs. The harness moved; "
            "every other cell is measured against a baseline that is not the "
            "pre-registered configuration. Stop."
        )
    n1 = sum(1 for r in rows if r["cell"] == 0)
    print(f"\nCELL 1 REPRODUCES E2: {n1}/{n1} runs to 1e-9.")

    # out-of-cell checks on whichever cell won, chosen after the fact
    meds = {ci: float(np.median(by_instance(
                [r for r in rows if r["cell"] == ci and not r.get("failed")], "regret")))
            for ci in range(len(CELLS))
            if any(r["cell"] == ci and not r.get("failed") for r in rows)}
    best = min(meds, key=meds.get)
    print(f"Best cell #{best + 1} ({cell_name(CELLS[best])}); running the two "
          f"out-of-cell checks.", flush=True)
    extra = [(best, i, s, DIM, 0.10) for i in range(N_INSTANCES) for s in range(N_SEEDS)]
    extra += [(best, i, s, 8, 0.25) for i in range(N_INSTANCES) for s in range(N_SEEDS)]
    with Pool(7) as pool:
        rows += list(pool.imap_unordered(_run, extra))

    Path("results").mkdir(exist_ok=True)
    Path("results/exploratory-three-factor.json").write_text(json.dumps(rows, indent=1))
    report(rows)


if __name__ == "__main__":
    main()
