"""Q62 — TuRBO-1 qLogNEI vs stored qLogNEI / DoE.

    python scripts/run_q62_turbo.py --check-gate
    python scripts/run_q62_turbo.py --smoke
    python scripts/run_q62_turbo.py --workers 2
    python scripts/run_q62_turbo.py --budget 200 --workers 2

Ticket Q62. Does not overwrite E2 or Q56. Q60/Q61 remain confirmation / q=1.

Frozen hyperparameters live in boec.turbo. Restart keeps history. Stored-JSON
gate: E2 qLogNEI instance means at d=6 must round to 0.1532 (σ=0.25) and
0.0808 (σ=0.10) before any TuRBO row is written.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

# BoTorch retries internally; the stderr flood is not a Q62 result.
warnings.filterwarnings("ignore", message="Optimization failed")
warnings.filterwarnings("ignore", message="A not p.d.")

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import Campaign, CampaignConfig  # noqa: E402
from boec.diagnostics import instance_bootstrap  # noqa: E402
from boec.oracles import load_ensemble  # noqa: E402
from boec.optimizers import AcqConfig  # noqa: E402
from boec.torch_oracle import BiphasicOracle  # noqa: E402
from boec.turbo import (  # noqa: E402
    LENGTH_INIT,
    LENGTH_MAX,
    LENGTH_MIN,
    collapse_rate as turbo_collapse_rate,
    n_unique_locations,
    score_finished_campaign,
)

E2 = ROOT / "results" / "e2-grid.json"
Q56 = ROOT / "results" / "q56-doe-ascent.json"
N_INSTANCES = 25
N_SEEDS = 2
DIM = 6
LOCKED = {(6, 0.25): 0.1532, (6, 0.10): 0.0808}
COLLAPSE_UNIQUE = 20


def unit_bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def e2_rows() -> list[dict]:
    return json.loads(E2.read_text())


def stored_arm_instance_means(arm: str, dim: int, sigma: float,
                              key: str = "regret") -> tuple[list[str], np.ndarray]:
    rows = [r for r in e2_rows()
            if r["arm"] == arm and r["dim"] == dim
            and abs(float(r["sigma"]) - sigma) < 1e-12]
    by: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by[r["instance"]].append(float(r[key]))
    inst = sorted(by)
    return inst, np.array([float(np.mean(by[i])) for i in inst])


def check_stored_gate() -> None:
    if not E2.exists():
        raise SystemExit(f"Q62 gate failed: missing {E2}")
    for (dim, sigma), locked in LOCKED.items():
        _, mu_vec = stored_arm_instance_means("qlognei", dim, sigma)
        mu = float(mu_vec.mean())
        if round(mu, 4) != locked:
            raise SystemExit(
                f"Q62 gate failed: stored qLogNEI d={dim} σ={sigma} mean "
                f"{mu:.6f} does not round to {locked}. No TuRBO rows written."
            )
        print(f"  stored qLogNEI d={dim} σ={sigma}: {mu:.4f} (locked {locked})")


def collapse_rate(rows: list[dict], thresh: int = COLLAPSE_UNIQUE) -> float:
    by: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        by[r["instance"]].append(int(r["n_unique"]))
    return turbo_collapse_rate(list(by.values()), thresh=thresh)


def q56_path_argmax_hits(sigma: float, target: float = 0.10) -> dict:
    """Stored Q56 landscape-level arrivals (rule A / measured argmax), two seeds averaged by first-hit-both? No: Q56 uses two-seed arrival helper.

    We report the published cell count from analyses so Q62 does not re-invent Q56.
    """
    if not Q56.exists():
        return {}
    data = json.loads(Q56.read_text())
    for block in data.get("analyses", []):
        if block.get("ascent_rule") != "path_argmax":
            continue
        for cell in block.get("cells", []):
            if cell.get("rule") != "rule_a":
                continue
            if abs(float(cell["sigma"]) - sigma) > 1e-12:
                continue
            if abs(float(cell["target"]) - target) > 1e-12:
                continue
            return dict(
                n=int(cell["n"]),
                hits_doe_ascent=int(cell["hits_ascent"]),
                hits_qlogei=int(cell["hits_qlogei"]),
                target=target,
            )
    return {}


def _one(payload: dict) -> dict:
    torch.set_num_threads(1)
    insts = {i.instance_id: i for i in load_ensemble(dim=DIM)[:N_INSTANCES]}
    inst = insts[payload["instance"]]
    sigma, seed, budget = payload["sigma"], payload["seed"], payload["budget"]
    bounds = unit_bounds(DIM)
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cfg = CampaignConfig(
        d=DIM, budget=budget, q=4, seed=seed,
        acq=AcqConfig(kind="qlognei"),
        use_turbo=True,
    )
    t0 = time.perf_counter()
    c = Campaign(orc, bounds, cfg)
    c.run()
    elapsed = time.perf_counter() - t0
    scored = score_finished_campaign(
        c, orc.truth(c.train_X), c.train_Y, float(inst.optimum_value),
    )
    assert scored["n_unique"] == n_unique_locations(c.train_X)
    row = dict(
        instance=inst.instance_id, dim=DIM, sigma=sigma, seed=seed,
        arm="turbo1_qlognei", budget=budget, elapsed_s=elapsed,
        length_init=LENGTH_INIT, length_min=LENGTH_MIN, length_max=LENGTH_MAX,
        **scored,
    )
    return row


def _summarise(rows: list[dict], budget: int) -> list[dict]:
    out = []
    by_sigma: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        by_sigma[r["sigma"]].append(r)
    for sigma, rs in sorted(by_sigma.items()):
        ids = sorted({r["instance"] for r in rs})
        turbo = np.array([
            np.mean([r["R_measured"] for r in rs if r["instance"] == i])
            for i in ids
        ])
        search = np.array([
            np.mean([r["R_search"] for r in rs if r["instance"] == i])
            for i in ids
        ])
        nei_ids, nei = stored_arm_instance_means("qlognei", DIM, sigma)
        doe_ids, doe = stored_arm_instance_means("doe", DIM, sigma)
        nei_map = dict(zip(nei_ids, nei))
        doe_map = dict(zip(doe_ids, doe))
        missing = [i for i in ids if i not in nei_map or i not in doe_map]
        if missing:
            raise SystemExit(f"Q62 instance ids missing from E2: {missing[:3]}")
        nei_v = np.array([float(nei_map[i]) for i in ids])
        doe_v = np.array([float(doe_map[i]) for i in ids])
        d_nei = turbo - nei_v
        d_doe = doe_v - turbo  # Paper sign: DoE − BO; negative favours DoE
        m_nei, lo_nei, hi_nei = instance_bootstrap(d_nei, n_boot=2000)
        m_doe, lo_doe, hi_doe = instance_bootstrap(d_doe, n_boot=2000)
        hit10 = 0
        for i in ids:
            seed_hits = [
                r["arrivals"].get("0.10") is not None
                for r in rs if r["instance"] == i
            ]
            if seed_hits and all(seed_hits):
                hit10 += 1
        cell = dict(
            sigma=sigma,
            budget=budget,
            n=len(ids),
            turbo_measured=float(turbo.mean()),
            turbo_search=float(search.mean()),
            turbo_id=float((turbo - search).mean()),
            turbo_gp_box=float(np.mean([
                np.mean([r["R_gp_box"] for r in rs if r["instance"] == i])
                for i in ids
            ])) if all(r["R_gp_box"] is not None for r in rs) else None,
            turbo_gp_tr=float(np.mean([
                np.mean([r["R_gp_tr"] for r in rs if r["instance"] == i])
                for i in ids
            ])) if all(r["R_gp_tr"] is not None for r in rs) else None,
            e2_n48_qlognei=float(nei_v.mean()),
            e2_n48_doe=float(doe_v.mean()),
            hit_regret_0_10_both_seeds=hit10,
            mean_unique=float(np.mean([r["n_unique"] for r in rs])),
            mean_restarts=float(np.mean([r["n_restarts"] for r in rs])),
            q56_rule_a_0_10=q56_path_argmax_hits(sigma, 0.10) if budget >= 48 else {},
        )
        if budget == 48:
            cell["stored_qlognei"] = cell["e2_n48_qlognei"]
            cell["stored_doe"] = cell["e2_n48_doe"]
            cell["turbo_minus_qlognei"] = {"mean": m_nei, "lo": lo_nei, "hi": hi_nei}
            cell["doe_minus_turbo"] = {"mean": m_doe, "lo": lo_doe, "hi": hi_doe}
        else:
            cell["stored_qlognei"] = None
            cell["stored_doe"] = None
            cell["turbo_minus_qlognei"] = None
            cell["doe_minus_turbo"] = None
            cell["budget_note"] = (
                "E2 qLogNEI/DoE means are 48-well. Do not subtract them from N=200 "
                "TuRBO regret. Use hit_regret_0_10_both_seeds vs Q56 doe_ascent."
            )
        out.append(cell)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-gate", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--sigma", type=float, default=None)
    ap.add_argument("--budget", type=int, default=48, choices=(48, 200))
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out_path = args.out or (ROOT / "results" / (
        "q62-turbo.json" if args.budget == 48 else "q62-turbo-n200.json"
    ))

    print("Q62 TuRBO-1 — frozen BoTorch defaults; restart keeps history")
    check_stored_gate()
    if args.check_gate:
        return

    insts = load_ensemble(dim=DIM)[:N_INSTANCES]
    sigmas = [args.sigma] if args.sigma is not None else [0.25, 0.10]
    seeds = [0] if args.smoke else list(range(N_SEEDS))
    if args.smoke:
        insts = insts[:1]
        sigmas = [0.25]

    jobs = [
        dict(instance=inst.instance_id, sigma=sigma, seed=seed, budget=args.budget)
        for sigma in sigmas for inst in insts for seed in seeds
    ]
    rows: list[dict] = []
    if args.workers <= 1:
        for job in jobs:
            row = _one(job)
            rows.append(row)
            print(
                f"  {row['instance'][:8]} σ={row['sigma']} seed={row['seed']}  "
                f"R_meas={row['R_measured']:.4f}  unique={row['n_unique']}/{row['n_observed']}  "
                f"restarts={row['n_restarts']}",
                flush=True,
            )
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(_one, job): job for job in jobs}
            for fut in as_completed(futs):
                row = fut.result()
                rows.append(row)
                print(
                    f"  {row['instance'][:8]} σ={row['sigma']} seed={row['seed']}  "
                    f"R_meas={row['R_measured']:.4f}  unique={row['n_unique']}/{row['n_observed']}",
                    flush=True,
                )
        rows.sort(key=lambda r: (r["sigma"], r["instance"], r["seed"]))

    collapse = collapse_rate(rows)
    print(f"collapse (<{COLLAPSE_UNIQUE} unique on every seed of a landscape): {collapse:.2f}")
    if collapse > 0.5:
        print("  TR collapsed on more than half of landscapes; do not retune length_init.")

    summary = _summarise(rows, args.budget)
    for s in summary:
        q56 = s.get("q56_rule_a_0_10") or {}
        if s.get("doe_minus_turbo"):
            print(
                f"σ={s['sigma']} N={s['budget']}  turbo={s['turbo_measured']:.4f}  "
                f"qLogNEI={s['stored_qlognei']:.4f}  DoE={s['stored_doe']:.4f}  "
                f"DoE−turbo={s['doe_minus_turbo']['mean']:+.4f} "
                f"[{s['doe_minus_turbo']['lo']:+.4f},{s['doe_minus_turbo']['hi']:+.4f}]"
            )
        else:
            print(
                f"σ={s['sigma']} N={s['budget']}  turbo={s['turbo_measured']:.4f}  "
                f"hit τ=0.10 both seeds={s['hit_regret_0_10_both_seeds']}/{s['n']}  "
                f"Q56 doe_ascent={q56.get('hits_doe_ascent')}/{q56.get('n')}  "
                f"Q56 qLogEI={q56.get('hits_qlogei')}/{q56.get('n')}  "
                f"(E2 48-well means not subtracted)"
            )

    payload = dict(
        ticket="Q62",
        smoke=bool(args.smoke),
        budget=args.budget,
        note="TuRBO-1 qLogNEI; keep_history on restart; do not overwrite E2/Q56. "
             "Smoke JSON is not a locked result.",
        hyperparameters=dict(
            length_init=LENGTH_INIT, length_min=LENGTH_MIN, length_max=LENGTH_MAX,
            keep_history=True, acquisition="qlognei", n_init="2d+2",
        ),
        rows=rows,
        summary=summary,
        collapse_rate=collapse,
    )
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
