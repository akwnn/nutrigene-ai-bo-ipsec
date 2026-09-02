"""LB -- SPADE vs qLogNEI at every matched round count.
Registered in docs/SPADE-ROUND-SWEEP-SPEC.md, frozen at 4411e5e BEFORE this file existed.

Both arms get the IDENTICAL schedule (n_init = 48-8(R-1), then R-1 batches of 8). The only
difference is how each batch is chosen: qLogNEI's acquisition, or SPADE's
certificate-contour straddle.
"""
from __future__ import annotations

import argparse, gc, importlib.util, json, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

C_GRID = (1.0, 1.5, 2.0, 3.0, 4.0)
ROUNDS = (2, 3, 4, 5)
BUDGET, QBATCH = 48, 8


def _mod(name, fn):
    sp = importlib.util.spec_from_file_location(name, str(ROOT / "scripts" / fn))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


_KV = None


def kv():
    global _KV
    if _KV is None:
        _KV = _mod("_lb_kv", "run_kv_plate2_certificate.py")
    return _KV


def build(family, arm, seed, rounds):
    from boec.campaign import AcqConfig, Campaign, CampaignConfig
    from boec.multiround import multiround_design, round_schedule
    from boec.replay import unit_bounds

    P = kv().p8()
    n_init, batches = round_schedule(BUDGET, rounds, BUDGET - QBATCH * (rounds - 1))
    orc = P.evaluator_for(family, family, seed)
    if arm == "spade":
        mu_max = float(getattr(orc, "mu_max", 1.0))
        return multiround_design(orc, P.DIM, seed, mu_max, n_init, batches, rho=0.95)
    cfg = CampaignConfig(d=P.DIM, budget=BUDGET, q=QBATCH, n_init=n_init, seed=seed,
                         acq=AcqConfig(kind="qlognei"))
    c = Campaign(orc, unit_bounds(P.DIM), cfg)
    c.run()
    return c.train_X, c.train_Y, c.train_Yvar


def score(family, seed, arm, rounds, X_sub, tau_by_p):
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    P = kv().p8(); p2 = P.p2()
    ev = P.evaluator_for(family, family, seed)
    X, Y, Yvar = build(family, arm, seed, rounds)
    with torch.no_grad():
        truth = ev.truth(X_sub).reshape(-1).double()
    regret = float(1.0 - scored_curve(ev, X, Y)[-1])
    m = build_gp(X, Y, Yvar, unit_bounds(P.DIM))
    with torch.no_grad():
        post = m.posterior(X_sub)
        mean = post.mean.reshape(-1, 1).double()
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        z = torch.randn(cov.shape[0], P.N_DRAWS,
                        generator=torch.Generator().manual_seed(seed), dtype=torch.double)
    rows = []
    for c in C_GRID:
        with torch.no_grad():
            draws = (mean + float(c) * L @ z).T
            for p, tau in tau_by_p.items():
                rows.append({"family": family, "seed": seed, "arm": arm,
                             "rounds": rounds, "regret": regret, "p_value": p,
                             "tau": tau, "inflation_c": float(c),
                             "n_wells": int(X.shape[0]),
                             **p2.vorobev_columns(draws, truth, tau, p2.ALPHAS)})
        del draws
    del m; gc.collect()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--families", default="ackley,hartmann6,levy,rosenbrock")
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "lb-round-sweep.json")
    a = ap.parse_args()

    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid

    P = kv().p8(); p2 = P.p2()
    fams = a.families.split(",")
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    tau_by = {}
    for f in fams:
        with torch.no_grad():
            t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
        tau_by[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10, 0.03, 0.01)}

    jobs = [(f, s) for s in range(a.seeds) for f in fams]
    rows, t0, done = [], time.time(), 0
    for family, seed in jobs:
        for R in ROUNDS:
            for arm in ("spade", "qlognei"):
                try:
                    rows += score(family, seed, arm, R, X_sub, tau_by[family])
                except Exception as e:
                    print(f"  !! {family} s{seed} {arm} R{R}: {type(e).__name__}: {e}",
                          flush=True)
        done += 1
        if a.pilot and done >= a.pilot:
            dt = (time.time() - t0) / done
            print(f"PILOT · {done} jobs · {dt:.1f}s each · projected "
                  f"{dt*len(jobs)/3600:.2f} h", flush=True)
            print("TIMING ONLY -- nothing written", flush=True)
            return
        if done % 2 == 0:
            el = (time.time() - t0) / 60
            print(f"[{done:3d}/{len(jobs)}] s{seed} {family:<11} rows={len(rows):6d} "
                  f"({el:.1f}m, {60*el/done:.0f}s/job)", flush=True)
            a.out.write_text(json.dumps({"status": "PARTIAL", "rows": rows}))
    a.out.write_text(json.dumps(rows))
    print(f"WROTE {a.out} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
