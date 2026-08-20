"""Q61 -- is the 0.0595 lead batching (q=4) rather than the terminal rule?

    .venv/bin/python scripts/run_q61_q1_sequential.py [n_instances] [--workers 3]
    .venv/bin/python scripts/run_q61_q1_sequential.py --shadow-only

Primary cell only. DoE and q=4 are READ from stored JSON. New campaigns are
qLogEI and qLogNEI at q=1 (35 rounds).
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

from boec.campaign import Campaign, CampaignConfig, batch_plan  # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.optimizers import AcqConfig  # noqa: E402
from boec.oracles import load_ensemble  # noqa: E402
from boec.torch_oracle import BiphasicOracle  # noqa: E402

DIM, SIGMA, BUDGET, Q1, Q4 = 6, 0.25, 48, 1, 4
N_INSTANCES, N_SEEDS = 25, 2
N_BOOT = 4000
CELL_TOL = 5e-5
GATE_TOL = 1e-12
PUBLISHED_Q4 = 0.1553
PUBLISHED_DOE = 0.0958
OUT = ROOT / "results" / "q61-q1-sequential.json"
E2 = ROOT / "results" / "e2-grid.json"
Q57 = ROOT / "results" / "q57-search-vs-id.json"
RULE = "=" * 100


def _rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else data.get("rows", data)


def _bounds() -> torch.Tensor:
    return torch.stack(
        [torch.zeros(DIM, dtype=torch.double), torch.ones(DIM, dtype=torch.double)]
    )


def _n_rounds(q: int) -> int:
    n_init, batches = batch_plan(DIM, BUDGET, q)
    return 1 + len(batches)


def _score(truth: torch.Tensor, Y: torch.Tensor, opt: float) -> dict:
    t = truth.double().reshape(-1)
    measured = opt - float(reported_best_curve(truth, Y)[-1])
    tested = opt - float(t.max())
    return dict(measured=measured, tested=tested)


def _run_bo(inst, seed: int, q: int, kind: str) -> dict:
    oracle = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    camp = Campaign(
        oracle,
        _bounds(),
        CampaignConfig(d=DIM, budget=BUDGET, q=q, seed=seed, acq=AcqConfig(kind=kind)),
    )
    camp.run()
    return _score(oracle.truth(camp.train_X), camp.train_Y, float(inst.optimum_value)) | {
        "n_visited": int(camp.train_X.shape[0]),
        "n_rounds": _n_rounds(q),
    }


def shadow_q4() -> None:
    """Two stored seeds must still reproduce published q=4 measured-argmax."""
    e2 = {
        (r["instance"], int(r["seed"])): float(r["regret"])
        for r in _rows(E2)
        if r["arm"] == "qlogei" and r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12
    }
    cell_mean = float(np.mean(list(e2.values())))
    if abs(cell_mean - PUBLISHED_Q4) > CELL_TOL:
        raise AssertionError(
            f"stored q=4 cell mean is {cell_mean:.6f}, published {PUBLISHED_Q4} "
            f"(|delta|={abs(cell_mean - PUBLISHED_Q4):.2e} > {CELL_TOL:g}). Stop."
        )
    ens = load_ensemble(dim=DIM)
    for seed in (0, 1):
        inst = ens[0]
        got = _run_bo(inst, seed, Q4, "qlogei")["measured"]
        want = e2[(inst.instance_id, seed)]
        if abs(got - want) > GATE_TOL:
            raise AssertionError(
                f"q=4 shadow failed at seed={seed}: {got:.15f} vs {want:.15f}. Stop."
            )
    print(f"  q=4 shadow ok (cell mean {cell_mean:.4f}, two rows at 1e-12)")


def one(job: tuple[int, int]) -> dict:
    idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM)[idx]
    out = dict(instance=inst.instance_id, instance_index=idx, seed=seed, sigma=SIGMA, n_rounds=_n_rounds(Q1))
    for tag, kind in (("qlogei", "qlogei"), ("qlognei", "qlognei")):
        score = _run_bo(inst, seed, Q1, kind)
        if score["n_visited"] != BUDGET:
            raise AssertionError(f"{kind} q=1 visited {score['n_visited']}, not {BUDGET}")
        if score["n_rounds"] != 35:
            raise AssertionError(f"{kind} q=1 ran {score['n_rounds']} rounds, not 35")
        out[tag] = score
    out["secs"] = round(time.time() - t0, 1)
    return out


def _per_instance(rows: list[dict], path: tuple[str, ...]) -> np.ndarray:
    by: dict[str, list[float]] = {}
    for row in rows:
        value = row
        for key in path:
            value = value[key]
        by.setdefault(row["instance"], []).append(float(value))
    return np.array([float(np.mean(v)) for _, v in sorted(by.items())])


def _stored_e2(arm: str) -> np.ndarray:
    sub = [
        r
        for r in _rows(E2)
        if r["arm"] == arm and r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12
    ]
    return _per_instance(sub, ("regret",))


def _stored_q57(key: str) -> np.ndarray:
    sub = [r for r in _rows(Q57) if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12]
    return _per_instance(sub, (key,))


def analyse(rows: list[dict]) -> dict:
    from scipy import stats

    q4 = _stored_e2("qlogei")
    doe_m = _stored_e2("doe")
    if abs(float(q4.mean()) - PUBLISHED_Q4) > CELL_TOL:
        raise AssertionError("q=4 stored mean drifted; refuse to contrast against it")
    if abs(float(doe_m.mean()) - PUBLISHED_DOE) > CELL_TOL:
        raise AssertionError("DoE stored mean drifted; refuse to contrast against it")
    doe_t = _stored_q57("doe_oracle_best")
    q4_t = _stored_q57("bo_oracle_best")
    nei4_m = _stored_e2("qlognei")
    nei4_t = _stored_q57("nei_oracle_best")

    def pack(name: str, a: np.ndarray, b: np.ndarray) -> dict:
        diff = a - b
        mean, lo, hi = instance_bootstrap(diff, n_boot=N_BOOT)
        wilcoxon = stats.wilcoxon(diff) if np.any(diff != 0) else None
        return dict(
            name=name,
            mean=float(mean),
            lo=float(lo),
            hi=float(hi),
            wilcoxon_p=float(wilcoxon.pvalue) if wilcoxon is not None else 1.0,
            a=float(a.mean()),
            b=float(b.mean()),
            n=int(diff.size),
        )

    q1_ei_m = _per_instance(rows, ("qlogei", "measured"))
    q1_ei_t = _per_instance(rows, ("qlogei", "tested"))
    q1_nei_m = _per_instance(rows, ("qlognei", "measured"))
    q1_nei_t = _per_instance(rows, ("qlognei", "tested"))
    return dict(
        n_rounds_q1=_n_rounds(Q1),
        n_rounds_q4=_n_rounds(Q4),
        contrasts=[
            pack("doe-q1_qlogei|measured", doe_m, q1_ei_m),
            pack("doe-q1_qlognei|measured", doe_m, q1_nei_m),
            pack("doe-q4_qlogei|measured", doe_m, q4),
            pack("q1-q4_qlogei|measured", q1_ei_m, q4),
            pack("doe-q1_qlogei|tested", doe_t, q1_ei_t),
            pack("doe-q1_qlognei|tested", doe_t, q1_nei_t),
            pack("q1-q4_qlogei|tested", q1_ei_t, q4_t),
            pack("doe-q4_qlognei|measured", doe_m, nei4_m),
            pack("q1-q4_qlognei|measured", q1_nei_m, nei4_m),
            pack("q1-q4_qlognei|tested", q1_nei_t, nei4_t),
        ],
    )


def report(analysis: dict) -> None:
    print(f"\n{RULE}\n  Q61 q=1 vs stored q=4 and DoE  (d={DIM}, sigma={SIGMA}, n=25)\n{RULE}")
    print(f"    q=1 rounds: {analysis['n_rounds_q1']}   q=4 rounds: {analysis['n_rounds_q4']}")
    for contrast in analysis["contrasts"]:
        print(
            f"    {contrast['name']:<32} {contrast['mean']:+.4f} "
            f"[{contrast['lo']:+.4f}, {contrast['hi']:+.4f}]   "
            f"a={contrast['a']:.4f} b={contrast['b']:.4f}  p={contrast['wilcoxon_p']:.4f}"
        )
    primary = next(c for c in analysis["contrasts"] if c["name"] == "doe-q1_qlogei|measured")
    print("\n    Registered falsifiers (measured-argmax, qLogEI q=1 vs DoE):")
    print(f"    {primary['mean']:+.4f} [{primary['lo']:+.4f}, {primary['hi']:+.4f}]")
    if primary["lo"] <= 0 <= primary["hi"] or primary["mean"] > 0:
        print("    Batching objection OPEN: q=1 vs DoE covers 0 or flipped.")
    elif primary["hi"] < 0:
        print("    Batching objection CLOSED: q=1 still loses; interval excludes 0.")
        print("    Report 35 rounds beside the 10-round q=4 arm.")
    else:
        print("    q=1 ahead of DoE (interval excludes 0). Report it; do not bury it.")


def _provenance(argv: list[str]) -> dict:
    def _git(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:  # noqa: BLE001
            return "unknown"

    import botorch
    import gpytorch

    return dict(
        git_sha=_git("rev-parse", "HEAD"),
        git_dirty=bool(_git("status", "--porcelain")),
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        argv=list(argv),
        python=platform.python_version(),
        torch=torch.__version__,
        botorch=botorch.__version__,
        gpytorch=gpytorch.__version__,
        numpy=np.__version__,
        config=dict(
            dim=DIM,
            sigma=SIGMA,
            budget=BUDGET,
            q=Q1,
            n_init=2 * DIM + 2,
            n_rounds=_n_rounds(Q1),
            n_instances=N_INSTANCES,
            n_seeds=N_SEEDS,
            cell_tol=CELL_TOL,
            gate_tol=GATE_TOL,
            published_q4=PUBLISHED_Q4,
            published_doe=PUBLISHED_DOE,
            n_boot=N_BOOT,
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_instances", nargs="?", type=int, default=N_INSTANCES)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--shadow-only", action="store_true")
    args = ap.parse_args()

    print(f"{RULE}\nQ61 -- q=1 at the primary cell\n{RULE}")
    print(f"  d={DIM}, sigma={SIGMA}, {args.n_instances} x {N_SEEDS}, q=1 -> {_n_rounds(Q1)} rounds")
    shadow_q4()
    if args.shadow_only:
        return

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["instance_index"], r["seed"]) for r in done}
    todo = [(i, s) for s in range(N_SEEDS) for i in range(args.n_instances) if (i, s) not in have]
    print(f"  {len(todo)} q=1 campaigns to run on {args.workers} workers\n")
    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, row in enumerate(pool.map(one, todo), 1):
                done.append(row)
                OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv), rows=done), indent=1))
                if k % 5 == 0 or k == len(todo):
                    elapsed = time.time() - t0
                    print(
                        f"    {k:>4}/{len(todo)}  {elapsed/60:>5.1f} min, "
                        f"~{elapsed/k*(len(todo)-k)/60:>5.1f} min left",
                        flush=True,
                    )

    analysis = analyse(done)
    report(analysis)
    OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv), analysis=analysis, rows=done), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
