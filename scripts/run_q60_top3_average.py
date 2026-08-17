"""Q60 — average original + confirmation on the top-3 shortlist.

    python scripts/run_q60_top3_average.py [n_instances] [--workers 3]

Replay Q58 campaigns (same instance ids, seeds, both arms). The four Q58 rules
must reproduce per row at 1e-12 before the average column is trusted.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import Campaign, CampaignConfig                    # noqa: E402
from boec.diagnostics import instance_bootstrap                       # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.selection import (gate_against_q58, mean_of_replicates,     # noqa: E402
                            posterior_mean_at_visited, single_readout,
                            top_k_average, top_k_confirm)
from boec.surrogate import build_gp                                   # noqa: E402
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar           # noqa: E402

DIM, BUDGET, Q = 6, 48, 4
SIGMA = 0.25
N_INSTANCES, N_SEEDS = 25, 2
TOP_K = 3
N_BOOT = 4000
Q60_RULES = ("single", "replicate", "top3", "posterior", "top3_average")
RULE_COST = {"single": 0, "replicate": BUDGET, "top3": TOP_K,
             "posterior": 0, "top3_average": TOP_K}

OUT = ROOT / "results" / "q60-top3-average.json"
Q58_JSON = ROOT / "results" / "q58-selection-sensitivity.json"
RULE = "=" * 100


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(DIM, dtype=torch.double),
                        torch.ones(DIM, dtype=torch.double)])


def _yvar(Y: torch.Tensor, orac) -> torch.Tensor:
    v = _plug_in_yvar(Y.double().numpy(), orac.sigma_rel, orac.sigma_add)
    return torch.from_numpy(v)


def _pick_all(X, Y, V, Y2, Yc, truth, opt: float) -> dict:
    t = truth(X).double().reshape(-1)
    picks = {
        "single": single_readout(Y),
        "replicate": mean_of_replicates(Y, Y2),
        "top3": top_k_confirm(Y, Yc, k=TOP_K),
        "top3_average": top_k_average(Y, Yc, k=TOP_K),
    }
    model = build_gp(X, Y, V, _bounds())

    def mean(Z, _m=model):
        with torch.no_grad():
            return _m.posterior(Z).mean

    picks["posterior"] = posterior_mean_at_visited(mean, X)
    best = float(t.max())
    return {k: opt - float(t[i]) for k, i in picks.items()} | {
        "oracle_best": opt - best,
        "hit": {k: bool(abs(float(t[i]) - best) < 1e-12) for k, i in picks.items()},
    }


def one(job: tuple[int, int]) -> dict:
    idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM)[idx]
    opt = float(inst.optimum_value)
    b = _bounds()
    out: dict = {}

    o = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    camp = Campaign(o, b, CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=seed,
                                         acq=AcqConfig(kind="qlogei")))
    camp.run()
    X = camp.train_X
    Y2, _ = o.evaluate(X)
    Yc, _ = o.evaluate(X)
    out["bo"] = _pick_all(X, camp.train_Y, camp.train_Yvar, Y2, Yc, o.truth, opt)

    od = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    r = run_doe_arm(od, b, truth=od.truth, budget=BUDGET, seed=seed)
    Xd = r.X_visited
    Y2d, _ = od.evaluate(Xd)
    Ycd, _ = od.evaluate(Xd)
    out["doe"] = _pick_all(Xd, r.Y_visited, _yvar(r.Y_visited, od), Y2d, Ycd,
                           od.truth, opt)

    return dict(instance=inst.instance_id, instance_index=idx, seed=seed,
                sigma=SIGMA, secs=round(time.time() - t0, 1), arms=out)


def _per_instance(rows: list[dict], arm: str, key: str) -> np.ndarray:
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["instance"], []).append(r["arms"][arm][key])
    return np.array([float(np.mean(v)) for _, v in sorted(by.items())])


def analyse(rows: list[dict]) -> dict:
    from scipy import stats
    out = []
    for rule in Q60_RULES:
        bo = _per_instance(rows, "bo", rule)
        doe = _per_instance(rows, "doe", rule)
        d = doe - bo
        m, lo, hi = instance_bootstrap(d, n_boot=N_BOOT)
        w = stats.wilcoxon(d) if np.any(d != 0) else None
        out.append(dict(
            rule=rule, extra_wells=RULE_COST[rule], n=int(d.size),
            bo=float(bo.mean()), doe=float(doe.mean()),
            contrast=float(m), lo=float(lo), hi=float(hi),
            wilcoxon_p=float(w.pvalue) if w is not None else 1.0,
            significant=bool(hi < 0 or lo > 0),
            bo_hit=float(np.mean([r["arms"]["bo"]["hit"][rule] for r in rows])),
            doe_hit=float(np.mean([r["arms"]["doe"]["hit"][rule] for r in rows]))))
    ceiling = dict(bo=float(_per_instance(rows, "bo", "oracle_best").mean()),
                   doe=float(_per_instance(rows, "doe", "oracle_best").mean()))
    return dict(rules=out, ceiling=ceiling)


def report(a: dict) -> None:
    print(f"\n{RULE}\n  Q60 — TOP-3 AVERAGE ON THE SAME CAMPAIGNS AS Q58  "
          f"(d={DIM}, sigma={SIGMA}, n=25)\n{RULE}")
    print(f"    {'rule':>14}{'extra wells':>13}{'BO':>9}{'DoE':>9}"
          f"{'DoE - BO':>26}{'p':>9}")
    for r in a["rules"]:
        star = "*" if r["significant"] else " "
        print(f"    {r['rule']:>14}{r['extra_wells']:>13}{r['bo']:>9.4f}{r['doe']:>9.4f}"
              f"{r['contrast']:>+13.4f} [{r['lo']:>+.4f},{r['hi']:>+.4f}]{star}"
              f"{r['wilcoxon_p']:>8.4f}")
    avg = next(r for r in a["rules"] if r["rule"] == "top3_average")
    top3 = next(r for r in a["rules"] if r["rule"] == "top3")
    print(f"\n    top3 (confirmation alone): {top3['contrast']:+.4f} "
          f"[{top3['lo']:+.4f}, {top3['hi']:+.4f}]")
    print(f"    top3_average:              {avg['contrast']:+.4f} "
          f"[{avg['lo']:+.4f}, {avg['hi']:+.4f}]")
    if avg["lo"] > 0 or avg["hi"] < 0:
        print("    Falsifier hit: averaging restores a signed lead "
              "(interval excludes 0). Confirmation-alone is a discard-artefact.")
    else:
        print("    Averaging interval covers 0; equivalence not tested here "
              "(see TOST). Do not call this a tie.")


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return dict(git_sha=_git("rev-parse", "HEAD"),
                git_dirty=bool(_git("status", "--porcelain")),
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), argv=list(argv),
                python=platform.python_version(), torch=torch.__version__,
                botorch=botorch.__version__, gpytorch=gpytorch.__version__,
                numpy=np.__version__, scipy=scipy.__version__,
                config=dict(dim=DIM, sigma=SIGMA, budget=BUDGET, q=Q, top_k=TOP_K,
                            n_instances=N_INSTANCES, n_seeds=N_SEEDS,
                            rules=list(Q60_RULES), rule_cost=RULE_COST,
                            n_boot=N_BOOT, q58_gate_tol=1e-12))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_instances", nargs="?", type=int, default=N_INSTANCES)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    print(f"{RULE}\nQ60 — averaged top-3 confirmation at the primary cell\n{RULE}")
    print(f"  d={DIM}, sigma={SIGMA}, {args.n_instances} landscapes x {N_SEEDS} seeds")
    print(f"  rules {Q60_RULES}; extra wells {RULE_COST}\n")

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["instance_index"], r["seed"]) for r in done}
    todo = [(i, s) for s in range(N_SEEDS) for i in range(args.n_instances)
            if (i, s) not in have]
    if have:
        print(f"  resuming — {len(have)} campaigns on disk")
    print(f"  {len(todo)} to run on {args.workers} workers\n")

    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, row in enumerate(pool.map(one, todo), 1):
                done.append(row)
                OUT.write_text(json.dumps(
                    dict(provenance=_provenance(sys.argv), rows=done), indent=1))
                if k % 5 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f"    {k:>4}/{len(todo)}  {el/60:>5.1f} min, "
                          f"~{el/k*(len(todo)-k)/60:>5.1f} min left", flush=True)

    stored = json.loads(Q58_JSON.read_text())["rows"]
    g = gate_against_q58(done, stored)
    print(f"  Q58 gate: {g['rows_checked']} values, worst |delta|={g['worst_abs_delta']:.3e}")

    a = analyse(done)
    report(a)
    OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv), analysis=a,
                                   rows=done, q58_gate=g), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
