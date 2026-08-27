"""KX -- SPADE vs every comparator, at matched calibration.

Registered in `docs/SPADE-CALIBRATED-BENCHMARK-SPEC.md`, frozen at 08b9650 BEFORE this
file existed.

The certification path is byte-identical to KT-B's: same `vorobev_columns`, same seeded
generator, same subset, same inflation. **The only thing that differs between arms is
where the 48 wells are.** That is the entire experiment.
"""
from __future__ import annotations

import argparse, gc, importlib.util, json, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT_DEFAULT = ROOT / "results" / "kx-calibrated-benchmark.json"

#: KX §7. Wider than KT's -- a comparator may need far more inflation. A c* landing on
#: the ceiling is reported as TRUNCATED, not passed.
C_GRID = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0)

#: SPADE's own arm plus every comparator `boec.replay.regenerate` can build.
SPADE_ARM = "versionb"
COMPARATORS = ("qlognei", "qlogei", "sobol", "lhs", "random", "doe")
ARMS = (SPADE_ARM,) + COMPARATORS


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_KV = None


def kv():
    global _KV
    if _KV is None:
        _KV = _mod("_kx_kv", "run_kv_plate2_certificate.py")
    return _KV


def build_arm(family, arm, seed):
    """48 wells under `arm`'s own rule. SPADE routes through KV unchanged."""
    KV = kv(); P = KV.p8()
    if arm == SPADE_ARM:
        X, Y, Yvar, _ = KV.build(family, arm, seed)
        return X, Y, Yvar
    from boec.replay import regenerate
    rec = regenerate(family, P.DIM, P.SIGMA, seed, arm, family=family)
    return rec.X, rec.Y, rec.Yvar


def score(family, seed, arm, X_sub, tau_by_p):
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    KV = kv(); P = KV.p8(); p2 = P.p2()
    ev = P.evaluator_for(family, family, seed)
    X, Y, Yvar = build_arm(family, arm, seed)
    with torch.no_grad():
        truth_sub = ev.truth(X_sub).reshape(-1).double()
    regret = float(1.0 - scored_curve(ev, X, Y)[-1])

    m_full = build_gp(X, Y, Yvar, unit_bounds(P.DIM))
    with torch.no_grad():
        post = m_full.posterior(X_sub)
        mean = post.mean.reshape(-1, 1).double()
        cov0 = post.mvn.covariance_matrix.double()
        cov0 = cov0 + 1e-8 * torch.eye(cov0.shape[0], dtype=torch.double)
        L0 = torch.linalg.cholesky(cov0)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov0.shape[0], P.N_DRAWS, generator=g, dtype=torch.double)

    rows = []
    for c in C_GRID:
        with torch.no_grad():
            draws = (mean + (float(c) * L0) @ z).T
            for p_val, tau in tau_by_p.items():
                rows.append({"family": family, "seed": seed, "arm": arm, "dim": P.DIM,
                             "sigma": P.SIGMA, "regret": regret, "p_value": p_val,
                             "tau": tau, "inflation_c": float(c),
                             "n_wells": int(X.shape[0]),
                             **p2.vorobev_columns(draws, truth_sub, tau, p2.ALPHAS)})
        del draws
    del m_full
    gc.collect()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--families", default="levy,rosenbrock,ackley,hartmann6")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    a = ap.parse_args()

    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid

    KV = kv(); P = KV.p8(); p2 = P.p2()
    fams = a.families.split(",")
    arms = a.arms.split(",")
    # Identical grid, subset and tau construction to KT-B and KV. Any divergence here
    # would make the arms incomparable to the committed runs, so it is copied, not rederived.
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    tau_by_family = {}
    for f in fams:
        with torch.no_grad():
            t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
        tau_by_family[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10, 0.03, 0.01)}

    # SEED-MAJOR, deliberately. KX-1 is a leave-one-family-out comparison, so a
    # family-major loop would make every checkpoint useless: the first hours would hold
    # four complete families for no seeds rather than all four families for some seeds.
    # This ordering makes every checkpoint a balanced, analysable experiment.
    jobs = [(f, s) for s in range(a.seeds) for f in fams]
    rows, t0, done = [], time.time(), 0
    if True:
        for family, seed in jobs:
            tau_by_p = tau_by_family[family]
            for arm in arms:
                try:
                    rows += score(family, seed, arm, X_sub, tau_by_p)
                except Exception as e:                     # a comparator that cannot be
                    print(f"  !! {family} s{seed} {arm}: {type(e).__name__}: {e}",
                          flush=True)                      # rebuilt is reported, not hidden
            done += 1
            if a.pilot and done >= a.pilot:
                dt = (time.time() - t0) / done
                tot = dt * len(jobs)
                print(f"PILOT · {done} campaigns · {dt:.1f}s each "
                      f"· projected {tot/3600:.2f} h", flush=True)
                print("TIMING ONLY -- nothing written", flush=True)
                return
            if done % 4 == 0:
                el = (time.time() - t0) / 60
                print(f"[{done:3d}/{len(jobs)}] s{seed} {family:<11} rows={len(rows):6d} "
                      f"({el:.1f}m, {60*el/done:.0f}s/job)", flush=True)
                a.out.write_text(json.dumps(
                    {"status": "PARTIAL", "n_done": done, "rows": rows}))
    a.out.write_text(json.dumps(rows))
    print(f"WROTE {a.out} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
