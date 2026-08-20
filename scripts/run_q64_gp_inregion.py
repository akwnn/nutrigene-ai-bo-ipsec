"""Q64 — GP posterior-mean peak inside the sampled region (G1 / G6).

    python scripts/run_q64_gp_inregion.py --primary
    python scripts/run_q64_gp_inregion.py --workers 4

Does not overwrite q34 or q35. Region for BO wells is the axis-aligned box of
visited points, the analogue of DoE ``stage2_bounds``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import Campaign, CampaignConfig  # noqa: E402
from boec.diagnostics import instance_bootstrap  # noqa: E402
from boec.metrics import constrained_argmax, point_in_region, sampled_region_bounds  # noqa: E402
from boec.optimizers import AcqConfig  # noqa: E402
from boec.oracles import load_ensemble  # noqa: E402
from boec.surrogate import build_gp  # noqa: E402
from boec.torch_oracle import BiphasicOracle  # noqa: E402

N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
N_RESTARTS = 20
RAW_SAMPLES = 4096
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
OUT = ROOT / "results" / "q64-gp-inregion.json"


def _job_key(job: dict) -> tuple:
    return (job["instance"], job["dim"], job["sigma"], job["seed"], job["acq"])


def _row_key(row: dict) -> tuple:
    return (row["instance"], row["dim"], row["sigma"], row["seed"], row["acq"])


def _load_rows() -> list[dict]:
    if not OUT.exists():
        return []
    data = json.loads(OUT.read_text())
    return list(data.get("rows", []))


def _write_payload(rows: list[dict], *, primary_only: bool) -> None:
    rows.sort(key=lambda r: (r["dim"], r["sigma"], r["acq"], r["instance"], r["seed"]))
    summary = _summarise(rows)
    payload = dict(
        ticket="Q64",
        note="GP unconstrained vs sampled-region peak. Does not overwrite q34/q35.",
        region="axis-aligned bounding box of visited wells",
        primary_only=primary_only,
        rows=rows,
        summary=summary,
    )
    OUT.write_text(json.dumps(payload, indent=1) + "\n")


def _unit(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d), torch.ones(d)]).double()


def _mean_fn(model):
    def predict(Z: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return model.posterior(Z.double()).mean.reshape(-1, 1)
    return predict


def _one(payload: dict) -> dict:
    torch.set_num_threads(1)
    dim, sigma, seed = payload["dim"], payload["sigma"], payload["seed"]
    kind = payload["acq"]
    insts = {i.instance_id: i for i in load_ensemble(dim=dim)[:N_INSTANCES]}
    inst = insts[payload["instance"]]
    bounds = _unit(dim)
    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cfg = CampaignConfig(
        d=dim, budget=BUDGET, q=4, seed=seed,
        acq=AcqConfig(kind=kind),
    )
    t0 = time.perf_counter()
    c = Campaign(o, bounds, cfg).run()
    elapsed = time.perf_counter() - t0
    model = build_gp(c.train_X.detach(), c.train_Y.detach(), c.train_Yvar.detach(), bounds)
    predict = _mean_fn(model)
    region = sampled_region_bounds(c.train_X)
    x_box, _, _ = constrained_argmax(
        predict, bounds, n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES, seed=seed,
    )
    inside = point_in_region(x_box, region)
    x_reg, _, _ = constrained_argmax(
        predict, region, n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES, seed=seed,
    )
    opt = float(inst.optimum_value)
    r_box = float(opt - float(o.truth(x_box.reshape(1, -1)).reshape(-1)[0]))
    r_reg = float(opt - float(o.truth(x_reg.reshape(1, -1)).reshape(-1)[0]))
    return dict(
        instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed, acq=kind,
        elapsed_s=elapsed,
        R_gp_box=r_box, R_gp_region=r_reg,
        unconstrained_inside_sampled_region=inside,
        n_observed=int(c.n_observed),
    )


def _summarise(rows: list[dict]) -> list[dict]:
    out = []
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["dim"], r["sigma"], r["acq"])].append(r)
    for (dim, sigma, acq), rs in sorted(groups.items()):
        ids = sorted({r["instance"] for r in rs})
        box = np.array([np.mean([r["R_gp_box"] for r in rs if r["instance"] == i]) for i in ids])
        reg = np.array([np.mean([r["R_gp_region"] for r in rs if r["instance"] == i]) for i in ids])
        contain = np.array([
            np.mean([float(r["unconstrained_inside_sampled_region"]) for r in rs if r["instance"] == i])
            for i in ids
        ])
        d = box - reg
        m, lo, hi = instance_bootstrap(d, n_boot=2000)
        ir_m, ir_lo, ir_hi = instance_bootstrap(reg, n_boot=2000)
        box_m, box_lo, box_hi = instance_bootstrap(box, n_boot=2000)
        out.append(dict(
            dim=dim, sigma=sigma, acq=acq, n=len(ids),
            gp_unconstrained={"mean": box_m, "lo": box_lo, "hi": box_hi},
            gp_inregion={"mean": ir_m, "lo": ir_lo, "hi": ir_hi},
            unconstrained_minus_inregion={"mean": m, "lo": lo, "hi": hi},
            fraction_unconstrained_inside_region=float(contain.mean()),
        ))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--primary", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    cells = ((6, 0.25),) if args.primary else CELLS
    acqs = ("qlogei", "qlognei")
    jobs = []
    for dim, sigma in cells:
        for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
            for seed in range(N_SEEDS):
                for acq in acqs:
                    jobs.append(dict(
                        instance=inst.instance_id, dim=dim, sigma=sigma,
                        seed=seed, acq=acq,
                    ))
    done = _load_rows()
    have = {_row_key(r) for r in done}
    todo = [job for job in jobs if _job_key(job) not in have]
    print(f"Q64 GP in-region — {len(jobs)} campaigns", flush=True)
    if have:
        print(f"  resuming — {len(have)} rows on disk, {len(todo)} to run", flush=True)
    rows = done
    if args.workers <= 1:
        for k, job in enumerate(todo, 1):
            row = _one(job)
            rows.append(row)
            _write_payload(rows, primary_only=args.primary)
            print(
                f"  {row['acq']} d={row['dim']} σ={row['sigma']} "
                f"{row['instance'][:8]} seed={row['seed']}  "
                f"box={row['R_gp_box']:.4f} region={row['R_gp_region']:.4f} "
                f"inside={row['unconstrained_inside_sampled_region']}",
                flush=True,
            )
            if k % 5 == 0 or k == len(todo):
                print(f"    checkpoint {len(rows)}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(_one, job): job for job in todo}
            for k, fut in enumerate(as_completed(futs), 1):
                row = fut.result()
                rows.append(row)
                _write_payload(rows, primary_only=args.primary)
                print(
                    f"  {row['acq']} d={row['dim']} σ={row['sigma']} "
                    f"{row['instance'][:8]}  box={row['R_gp_box']:.4f} "
                    f"region={row['R_gp_region']:.4f} inside={row['unconstrained_inside_sampled_region']}",
                    flush=True,
                )
                if k % 5 == 0 or k == len(todo):
                    print(f"    checkpoint {len(rows)}/{len(jobs)}", flush=True)
    summary = _summarise(rows)
    for s in summary:
        print(
            f"d={s['dim']} σ={s['sigma']} {s['acq']}: "
            f"box={s['gp_unconstrained']['mean']:.4f}  "
            f"in-region={s['gp_inregion']['mean']:.4f}  "
            f"inside={s['fraction_unconstrained_inside_region']:.2%}  "
            f"box−region={s['unconstrained_minus_inregion']['mean']:+.4f}"
        )
    _write_payload(rows, primary_only=args.primary)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
