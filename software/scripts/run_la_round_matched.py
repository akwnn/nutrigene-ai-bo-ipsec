"""LA -- the round-matched benchmark. Registered in publication/manuscript/PROTOCOLS.md (LA)
frozen at 4cbe17e BEFORE this file existed.

KX compared `qlognei` at TEN adaptive rounds against SPADE at TWO. This holds rounds
fixed. `CampaignConfig(q=8, n_init=40)` gives a 40-well opening plus one batch of 8 --
exactly SPADE's 40 + 8 -- so the only thing that differs is HOW the last 8 wells are
chosen: qLogNEI's acquisition, or SPADE's straddle.
"""
from __future__ import annotations

import argparse, gc, importlib.util, json, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software" / "src"))
OUT = ROOT / "research" / "results" / "comparisons" / "la-round-matched.json"

C_GRID = (1.0, 1.5, 2.0, 3.0, 4.0)
ARMS = ("versionb", "spade_cert_rho95", "qlognei_r2", "qlognei_r10", "lhs")


def _mod(name, fn):
    sp = importlib.util.spec_from_file_location(name, str(ROOT / "software" / "scripts" / fn))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


_KV = None


def kv():
    global _KV
    if _KV is None:
        _KV = _mod("_la_kv", "run_kv_plate2_certificate.py")
    return _KV


def build(family, arm, seed):
    """48 wells. The ONLY difference between arms is where the last 8 go."""
    from boec.campaign import AcqConfig, Campaign, CampaignConfig
    from boec.replay import regenerate, unit_bounds

    KV = kv(); P = KV.p8()
    if arm in ("versionb", "spade_cert_rho95"):
        # `versionb` targets the TRUE contour (mean = tau), where P(f>tau)=0.5 -- points
        # that can never enter a certified region. `spade_cert_rho95` targets the
        # CERTIFIED contour (mean - z_rho*sd = tau), i.e. the edge of what would actually
        # be certified. The module has existed and been tested since KV; no arm has ever
        # used it against a CALIBRATED certificate, which is what KV-2 lacked.
        X, Y, Yvar, _ = KV.build(family, arm, seed)
        return X, Y, Yvar
    if arm == "lhs":
        rec = regenerate(family, P.DIM, P.SIGMA, seed, "lhs", family=family)
        return rec.X, rec.Y, rec.Yvar
    orc = P.evaluator_for(family, family, seed)
    # q=8 / n_init=40 -> 40 + one batch of 8 = 2 rounds, matching SPADE exactly.
    # q=4 / n_init=None -> 2d+2=14 opening then eights of four = 10 rounds (KX's config).
    q, n_init = (8, 40) if arm == "qlognei_r2" else (4, None)
    cfg = CampaignConfig(d=P.DIM, budget=48, q=q, n_init=n_init, seed=seed,
                         acq=AcqConfig(kind="qlognei"))
    c = Campaign(orc, unit_bounds(P.DIM), cfg)
    c.run()
    return c.train_X, c.train_Y, c.train_Yvar


def score(family, seed, arm, X_sub, tau_by_p):
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    KV = kv(); P = KV.p8(); p2 = P.p2()
    ev = P.evaluator_for(family, family, seed)
    X, Y, Yvar = build(family, arm, seed)
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
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], P.N_DRAWS, generator=g, dtype=torch.double)
    rows = []
    for c in C_GRID:
        with torch.no_grad():
            draws = (mean + float(c) * L @ z).T
            for p, tau in tau_by_p.items():
                rows.append({"family": family, "seed": seed, "arm": arm,
                             "regret": regret, "p_value": p, "tau": tau,
                             "inflation_c": float(c), "n_wells": int(X.shape[0]),
                             **p2.vorobev_columns(draws, truth, tau, p2.ALPHAS)})
        del draws
    del m
    gc.collect()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--families", default="ackley,hartmann6,levy,rosenbrock")
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid

    KV = kv(); P = KV.p8(); p2 = P.p2()
    fams = a.families.split(",")
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    tau_by = {}
    for f in fams:
        with torch.no_grad():
            t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
        tau_by[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10, 0.03, 0.01)}

    jobs = [(f, s) for s in range(a.seeds) for f in fams]   # seed-major: balanced checkpoints
    rows, t0, done = [], time.time(), 0
    for family, seed in jobs:
        for arm in ARMS:
            try:
                rows += score(family, seed, arm, X_sub, tau_by[family])
            except Exception as e:
                print(f"  !! {family} s{seed} {arm}: {type(e).__name__}: {e}", flush=True)
        done += 1
        if a.pilot and done >= a.pilot:
            dt = (time.time() - t0) / done
            print(f"PILOT · {done} jobs · {dt:.1f}s each · projected "
                  f"{dt*len(jobs)/3600:.2f} h", flush=True)
            print("TIMING ONLY -- nothing written", flush=True)
            return
        if done % 4 == 0:
            el = (time.time() - t0) / 60
            print(f"[{done:3d}/{len(jobs)}] s{seed} {family:<11} rows={len(rows):6d} "
                  f"({el:.1f}m, {60*el/done:.0f}s/job)", flush=True)
            a.out.write_text(json.dumps({"status": "PARTIAL", "rows": rows}))
    a.out.write_text(json.dumps(rows))
    print(f"WROTE {a.out} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
