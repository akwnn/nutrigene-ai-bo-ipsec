"""KT Lever B · posterior INFLATION sweep. Registered in SPADE-ASSURANCE-CALIBRATION-SPEC.md §2 (Lever B) and §3 (KT-5), frozen at 6848e2f, never run until now.

Registered in `docs/SPADE-SELECTION-BLIND-SPEC.md`, frozen at `09275d7` **before this file
existed**.

Mean from all 48 wells; joint covariance from the plate-1 40 wells only. Same seeded
generator, same `vorobev_columns`, same subset -- the ONLY change is which design the
covariance comes from. `plate1_only` has no plate 2 and must come out identical to KV; it is
the null control and any movement is a bug, reported not patched.
"""
from __future__ import annotations

import argparse, gc, importlib.util, json, subprocess, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT_DEFAULT = ROOT / "results" / "ktb-inflation.json"

#: KT §2 Lever B, registered grid. 1.0 is the identity control.
C_GRID = (1.0, 1.25, 1.5, 2.0)


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_KV = None


def kv():
    global _KV
    if _KV is None:
        _KV = _mod("_kw_kv", "run_kv_plate2_certificate.py")
    return _KV


def score_blind(family, seed, arm, X_sub, tau_by_p):
    from boec.replay import scored_curve, unit_bounds
    from boec.selectionblind import selection_blind_covariance
    from boec.surrogate import build_gp

    KV = kv(); P = KV.p8(); p2 = P.p2(); VB = KV.vb()
    ev = P.evaluator_for(family, family, seed)
    X, Y, Yvar, _ = KV.build(family, arm, seed)
    with torch.no_grad():
        truth_sub = ev.truth(X_sub).reshape(-1).double()
    regret = float(1.0 - scored_curve(ev, X, Y)[-1])

    b = unit_bounds(P.DIM)
    m_full = build_gp(X, Y, Yvar, b)

    # KT Lever B: scale the posterior SD by c >= 1 before drawing. Scaling SD shrinks the
    # excursion probability toward 0.5 monotonically, so the family of certified sets is
    # NESTED in c -- a legitimate RCPS lambda, exactly as alpha is. c=1.0 is the identity
    # control and MUST reproduce the standard certificate.
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
        # ERRATUM (mine): the gamma loop was redundant. `tau` comes from
        # `tau_quantile(p_val)` and never from gamma, so the six gamma values produced six
        # IDENTICAL rows differing only in a label -- verified directly on KV's output, where
        # ce_vol/ce_empirical/ce_contain/ce_empty/tau all take exactly 1 distinct value across
        # the six. The certificate was being computed 6x. Removing it changes no number: the
        # analyser averages a campaign's cells, and averaging 4 rows equals averaging the same
        # 4 rows repeated 6 times. KV's committed output keeps its duplicates; only the cost
        # changes here.
            for p_val, tau in tau_by_p.items():
                with torch.no_grad():
                    pmap = (draws >= tau).double().mean(dim=0)
                    map_err = float(((pmap >= 0.5) ^ (truth_sub >= tau)).double().mean())
                rows.append({"map_total_error_vol_sub": map_err, "family": family,
                             "seed": seed, "arm": arm, "dim": P.DIM, "sigma": P.SIGMA,
                             "regret": regret, "gamma": None, "p_value": p_val, "tau": tau,
                             "inflation_c": float(c), "n_wells": int(X.shape[0]),
                             **p2.vorobev_columns(draws, truth_sub, tau, p2.ALPHAS)})
        del draws
    del m_full
    gc.collect()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--families", type=str, default="levy,rosenbrock,ackley,hartmann6")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    a = ap.parse_args()

    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid

    KV = kv(); P = KV.p8(); p2 = P.p2()
    fams = tuple(a.families.split(","))
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    tau_by_family = {}
    for f in fams:
        with torch.no_grad():
            t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
        tau_by_family[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10, 0.03, 0.01)}

    seeds = range(a.pilot if a.pilot else a.seeds)
    jobs = [(f, s) for f in fams for s in seeds]
    rows, t0 = [], time.time()
    for n, (f, s) in enumerate(jobs, 1):
        for arm in KV.ARMS:
            rows.extend(score_blind(f, s, arm, X_sub, tau_by_family[f]))
        if a.pilot:
            continue
        if n % 10 == 0 or n == len(jobs):
            el = time.time() - t0
            print(f"[{n:3d}/{len(jobs)}] {f:<11} rows={len(rows):>6} "
                  f"({el/60:.1f}m, {el/(n*len(KV.ARMS)):.0f}s/campaign)", flush=True)
            a.out.write_text(json.dumps({"status": "PARTIAL", "n_done": n, "rows": rows}, indent=1))

    if a.pilot:
        dt = time.time() - t0; nc = len(jobs) * len(KV.ARMS)
        full = len(fams) * a.seeds * len(KV.ARMS)
        print(f"PILOT · {nc} campaigns · {dt/nc:.1f}s each · "
              f"projected {dt/nc*full/3600:.2f} h ({full} campaigns)")
        print("TIMING ONLY -- nothing written")
        return

    def git(*x):
        try:
            return subprocess.check_output(["git", *x], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:
            return "unknown"
    a.out.write_text(json.dumps(
        {"status": "COMPLETE", "spec": "docs/SPADE-SELECTION-BLIND-SPEC.md",
         "provenance": {"git_sha": git("rev-parse", "HEAD"),
                        "git_dirty": bool(git("status", "--porcelain"))},
         "rows": rows}, indent=1))
    print(f"\nwrote {a.out} · {len(rows)} rows")


if __name__ == "__main__":
    main()
