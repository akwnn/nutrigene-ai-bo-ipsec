"""Does SUR on certified volume beat the straddle proxies it was meant to stand in for?

Identical plate 1 (40 LHS), identical 400-point candidate grid, identical certification.
The ONLY difference is the plate-2 rule:
  straddle      -- Bryan's 1.96*sd - |mean - tau|          (the committed `versionb`)
  cert_straddle -- the rho-contour variant                 (LA's regret winner)
  sur           -- direct greedy maximisation of certified volume  (boec.sur)
"""
from __future__ import annotations

import importlib.util, json, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore"); torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

N_P1, N_P2, N_CAND = 40, 8, 400
CS = (1.0, 1.5, 2.0)


def _mod(n, f):
    sp = importlib.util.spec_from_file_location(n, str(ROOT / "scripts" / f))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def main():
    KV = _mod("kv", "run_kv_plate2_certificate.py")
    from boec.certstraddle import batch_lse_rho, certificate_straddle
    from boec.designspace import gp_adapter, tau_quantile
    from boec.lse import batch_lse, exclusion_radius, straddle_score
    from boec.norms import sobol_grid
    from boec.replay import unit_bounds
    from boec.runner import static_design
    from boec.sur import batch_sur
    from boec.surrogate import build_gp

    P = KV.p8(); p2 = P.p2()
    fams = ["ackley", "hartmann6", "levy", "rosenbrock"]
    seeds = range(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    tau_by = {}
    for f in fams:
        with torch.no_grad():
            t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
        tau_by[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10)}

    rows, t0 = [], time.time()
    b = unit_bounds(P.DIM)
    for fam in fams:
        for s in seeds:
            orc = P.evaluator_for(fam, fam, s)
            X1 = static_design(b, "lhs", N_P1, s)
            Y1, V1 = orc.evaluate(X1)
            m1 = build_gp(X1, Y1, V1, b)
            ad = gp_adapter(m1)
            cand = sobol_grid(P.DIM, N_CAND, seed=s)
            theta = 0.80 * float(getattr(orc, "mu_max", 1.0))
            with torch.no_grad():
                post = m1.posterior(cand)
                cmean = post.mean.reshape(-1, 1).double()
                ccov = post.mvn.covariance_matrix.double()
            mean_c, sd_c = ad.posterior_mean_and_sd(cand)
            rad = exclusion_radius(m1)
            noise = float(V1.mean())

            picks = {
                "straddle": batch_lse(ad, cand, theta, N_P2, exclude=rad, sigma=None),
                "cert_straddle": batch_lse_rho(ad, cand, theta, N_P2, exclude=rad,
                                               rho=0.95),
                "sur": cand[batch_sur(cmean, ccov, theta, 0.95, noise, N_P2,
                                      n_draws=400, seed=s, n_cand=120)],
            }
            for arm, X2 in picks.items():
                Y2, V2 = orc.evaluate(X2)
                X = torch.cat([X1, X2]); Y = torch.cat([Y1, Y2]); Yv = torch.cat([V1, V2])
                m = build_gp(X, Y, Yv, b)
                with torch.no_grad():
                    truth = orc.truth(X_sub).reshape(-1).double()
                    po = m.posterior(X_sub)
                    mu = po.mean.reshape(-1, 1).double()
                    cv = po.mvn.covariance_matrix.double()
                    cv = cv + 1e-8 * torch.eye(cv.shape[0], dtype=torch.double)
                    L = torch.linalg.cholesky(cv)
                    z = torch.randn(cv.shape[0], P.N_DRAWS,
                                    generator=torch.Generator().manual_seed(s),
                                    dtype=torch.double)
                    for c in CS:
                        draws = (mu + c * L @ z).T
                        for p, tau in tau_by[fam].items():
                            rows.append({"family": fam, "seed": s, "arm": arm, "c": c,
                                         "p": p,
                                         **p2.vorobev_columns(draws, truth, tau,
                                                              p2.ALPHAS)})
                        del draws
                del m
            del m1
        print(f"  {fam} done ({time.time()-t0:.0f}s)", flush=True)
    out = ROOT / "results" / "probe-sur-vs-straddle.json"
    out.write_text(json.dumps(rows))
    print(f"WROTE {out} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
