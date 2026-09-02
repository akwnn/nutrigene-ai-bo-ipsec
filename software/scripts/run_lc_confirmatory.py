"""LC -- the confirmatory run the paper's headline needs.

Closes three gaps at once:
  1. SPADE R=5 and qLogNEI R=10 measured IN ONE PROCESS, not paired across LA and LB.
  2. `hill` INCLUDED -- the biphasic dose-response family, absent from LA and LB and void
     in KZ-2 because tau was computed from instance 0 while each seed drew a different
     instance from the 40-member ensemble. Here tau is computed PER INSTANCE.
  3. Larger n, and the full matched-round sweep alongside, so LB's non-monotone R=4 tie
     gets a second look at higher power.
"""
from __future__ import annotations

import argparse, gc, importlib.util, json, sys, time, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore"); torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software" / "src"))

C_GRID = (1.0, 1.5, 2.0, 3.0)
BUDGET, QBATCH = 48, 8
#: (arm, rounds) pairs. r10 is qLogNEI's own best config; r5 is SPADE's.
CONFIGS = (("spade", 3), ("spade", 5), ("qlognei", 3), ("qlognei", 5), ("qlognei", 10))


def _mod(n, f):
    sp = importlib.util.spec_from_file_location(n, str(ROOT / "software" / "scripts" / f))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


_KV = None


def kv():
    global _KV
    if _KV is None:
        _KV = _mod("_lc_kv", "run_kv_plate2_certificate.py")
    return _KV


def instance_for(family, seed):
    """hill is keyed by instance_id; every other family by its own label."""
    if family != "hill":
        return family
    from boec.replay import load_ensemble
    ids = [i.instance_id for i in load_ensemble(kv().p8().DIM)]
    return ids[seed % len(ids)]


def build(family, arm, seed, rounds):
    from boec.campaign import AcqConfig, Campaign, CampaignConfig
    from boec.multiround import multiround_design, round_schedule
    from boec.replay import unit_bounds

    P = kv().p8()
    inst = instance_for(family, seed)
    orc = P.evaluator_for(family, inst, seed)
    if rounds == 10:
        n_init, q = None, 4                      # qLogNEI's committed 14 + eights of four
    else:
        n_init, q = BUDGET - QBATCH * (rounds - 1), QBATCH
    if arm == "spade":
        ni, batches = round_schedule(BUDGET, rounds, n_init)
        mu_max = float(getattr(orc, "mu_max", 1.0))
        return multiround_design(orc, P.DIM, seed, mu_max, ni, batches, rho=0.95), orc
    cfg = CampaignConfig(d=P.DIM, budget=BUDGET, q=q, n_init=n_init, seed=seed,
                         acq=AcqConfig(kind="qlognei"))
    c = Campaign(orc, unit_bounds(P.DIM), cfg)
    c.run()
    return (c.train_X, c.train_Y, c.train_Yvar), orc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=25)
    ap.add_argument("--families", default="hill,ackley,hartmann6,levy,rosenbrock")
    ap.add_argument("--out", type=Path, default=ROOT / "research" / "results" / "comparisons" / "lc-confirmatory.json")
    ap.add_argument("--resume", action="store_true",
                    help="Keep rows already in --out and skip those (family, seed) jobs. "
                         "Safe: every job is keyed by (family, seed) and all randomness "
                         "derives from seed, so a resumed job reproduces exactly.")
    a = ap.parse_args()

    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    P = kv().p8(); p2 = P.p2()
    fams = a.families.split(",")
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)

    tau_cache: dict = {}

    def taus(family, seed):
        """PER-INSTANCE tau. Getting this wrong voided KZ-2's hill rows."""
        inst = instance_for(family, seed)
        if inst not in tau_cache:
            with torch.no_grad():
                t = P.evaluator_for(family, inst, 0).truth(grid).reshape(-1).double()
            tau_cache[inst] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10)}
        return tau_cache[inst]

    rows, have = [], set()
    if a.resume and a.out.exists():
        prev = json.loads(a.out.read_text())
        rows = prev["rows"] if isinstance(prev, dict) else prev
        have = {(r["family"], r["seed"]) for r in rows}
        print(f"RESUME {a.out}: {len(rows)} rows, {len(have)} jobs already done",
              flush=True)
    jobs = [(f, s) for s in range(a.seeds) for f in fams if (f, s) not in have]
    t0, done = time.time(), 0
    for family, seed in jobs:
        tb = taus(family, seed)
        for arm, R in CONFIGS:
            try:
                (X, Y, Yvar), orc = build(family, arm, seed, R)
                with torch.no_grad():
                    truth = orc.truth(X_sub).reshape(-1).double()
                regret = float(1.0 - scored_curve(orc, X, Y)[-1])
                m = build_gp(X, Y, Yvar, unit_bounds(P.DIM))
                with torch.no_grad():
                    po = m.posterior(X_sub)
                    mu = po.mean.reshape(-1, 1).double()
                    cv = po.mvn.covariance_matrix.double()
                    cv = cv + 1e-8 * torch.eye(cv.shape[0], dtype=torch.double)
                    L = torch.linalg.cholesky(cv)
                    z = torch.randn(cv.shape[0], P.N_DRAWS,
                                    generator=torch.Generator().manual_seed(seed),
                                    dtype=torch.double)
                    for c in C_GRID:
                        draws = (mu + c * L @ z).T
                        for p, tau in tb.items():
                            rows.append({"family": family, "seed": seed, "arm": arm,
                                         "rounds": R, "regret": regret, "p_value": p,
                                         "inflation_c": float(c),
                                         "n_wells": int(X.shape[0]),
                                         **p2.vorobev_columns(draws, truth, tau,
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
