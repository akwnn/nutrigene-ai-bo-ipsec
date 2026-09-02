"""TAU -- is `hill`'s saturation a property of the family, or of `tau`?

Implements publication/manuscript/PROTOCOLS.md (TAU), frozen before this file was written.

Reuses run_lc_confirmatory.py's `build` verbatim, so p=0.30/0.10 must reproduce LC's
certification rates. That is the correctness gate (spec 6); if it fails, nothing here
is readable.

Records `margin_over_tau`, `noise_sd` and `margin_sd` per (family, seed, p) so TAU-1's
collapse can be tested directly rather than asserted.
"""
from __future__ import annotations

import argparse, gc, importlib.util, json, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore"); torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software" / "src"))

C_GRID = (1.0, 1.5, 2.0, 3.0)
P_GRID = (0.70, 0.50, 0.30, 0.20, 0.10)     # spec 2. LARGER p = EASIER target.
CONFIGS = (("spade", 5), ("qlognei", 5))     # the comparison that survived LC at 32 seeds
BUDGET = 48


def _mod(n, f):
    sp = importlib.util.spec_from_file_location(n, str(ROOT / "software" / "scripts" / f))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


_LC = None


def lc():
    global _LC
    if _LC is None:
        _LC = _mod("_tau_lc", "run_lc_confirmatory.py")
    return _LC


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=32)
    ap.add_argument("--families", default="hill,ackley,hartmann6,levy,rosenbrock")
    ap.add_argument("--out", type=Path, default=ROOT / "research" / "results" / "generalization" / "tau-sweep.json")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()

    L = lc()
    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    P = L.kv().p8(); p2 = P.p2()
    fams = a.families.split(",")
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)

    tau_cache: dict = {}

    def taus(family, seed):
        """PER-INSTANCE tau, plus the difficulty statistics TAU-1 needs."""
        inst = L.instance_for(family, seed)
        if inst not in tau_cache:
            with torch.no_grad():
                t = P.evaluator_for(family, inst, 0).truth(grid).reshape(-1).double()
            sig = float(getattr(P.evaluator_for(family, inst, 0), "sigma_rel", 0.25))
            d = {}
            for p in P_GRID:
                tau = float(tau_quantile(t, p))
                above = t[t >= tau]
                lvl = float(above.mean().abs()) if above.numel() else 0.0
                margin = float(above.mean() - tau) if above.numel() else 0.0
                sd = sig * lvl
                d[p] = {"tau": tau, "margin_over_tau": margin, "noise_sd": sd,
                        "margin_sd": (margin / sd) if sd > 0 else float("nan"),
                        "response_level": lvl}
            tau_cache[inst] = d
        return tau_cache[inst]

    rows, have = [], set()
    if a.resume and a.out.exists():
        prev = json.loads(a.out.read_text())
        rows = prev["rows"] if isinstance(prev, dict) else prev
        have = {(r["family"], r["seed"]) for r in rows}
        print(f"RESUME {a.out}: {len(rows)} rows, {len(have)} jobs done", flush=True)
    jobs = [(f, s) for s in range(a.seeds) for f in fams if (f, s) not in have]
    t0, done = time.time(), 0

    for family, seed in jobs:
        tb = taus(family, seed)
        for arm, R in CONFIGS:
            try:
                (X, Y, Yvar), orc = L.build(family, arm, seed, R)
                with torch.no_grad():
                    truth = orc.truth(X_sub).reshape(-1).double()
                regret = float(1.0 - scored_curve(orc, X, Y)[-1])
                m = build_gp(X, Y, Yvar, unit_bounds(P.DIM))
                with torch.no_grad():
                    po = m.posterior(X_sub)
                    mu = po.mean.reshape(-1, 1).double()
                    cv = po.mvn.covariance_matrix.double()
                    cv = cv + 1e-8 * torch.eye(cv.shape[0], dtype=torch.double)
                    Lc = torch.linalg.cholesky(cv)
                    z = torch.randn(cv.shape[0], P.N_DRAWS,
                                    generator=torch.Generator().manual_seed(seed),
                                    dtype=torch.double)
                    for c in C_GRID:
                        draws = (mu + c * Lc @ z).T
                        for p, st in tb.items():
                            rows.append({"family": family, "seed": seed, "arm": arm,
                                         "rounds": R, "regret": regret, "p_value": p,
                                         "inflation_c": float(c),
                                         "n_wells": int(X.shape[0]),
                                         **{k: v for k, v in st.items() if k != "tau"},
                                         **p2.vorobev_columns(draws, truth, st["tau"],
                                                              p2.ALPHAS)})
                        del draws
                del m; gc.collect()
            except Exception as e:
                print(f"  !! {family} s{seed} {arm} R{R}: {type(e).__name__}: {e}",
                      flush=True)
        done += 1
        if done % 2 == 0:
            el = (time.time() - t0) / 60
            print(f"[{done:3d}/{len(jobs)}] s{seed} {family:<11} rows={len(rows):6d} "
                  f"({el:.1f}m, {60*el/done:.0f}s/job)", flush=True)
            a.out.write_text(json.dumps({"status": "PARTIAL", "rows": rows}))
    a.out.write_text(json.dumps(rows))
    print(f"WROTE {a.out} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
