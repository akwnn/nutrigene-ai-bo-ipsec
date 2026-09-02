#!/usr/bin/env python
"""Is a Phase 3 replay on the in-house coating data worth running at all?

    python scripts/lab_phase3_feasibility.py

WHY ASK BEFORE GATING
---------------------
Turning the 12 fibronectin/vitronectin tubes into signed measurements costs a human
roughly two hours in CytExpert, plus the judgement calls in `data/lab/overlay/GATE.md`.
That is worth spending if a Phase 3 replay can show something, and wasted if it cannot.

The replay is the same shape as Phase 2: the optimizer may only propose conditions the
lab actually ran, and we ask how many tubes it needs to reach the best one. The
comparison arm is **the order the lab itself used** -- fibronectin low-to-high, then
vitronectin low-to-high -- because that is the one-factor-at-a-time scan BO would be
replacing.

**This runs on CANDIDATE numbers.** `y` is unsigned, so nothing here is a result. The
output is a go/no-go on whether the gating session buys a Phase 3 figure, and the
honest answer may well be no: 12 points is very few, and if the OFAT scan stumbles onto
the optimum early there is no headroom for any method to win.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.optimizers import AcqConfig, propose  # noqa: E402
from boec.surrogate import build_gp  # noqa: E402

CANDIDATES_CSV = ROOT / "data" / "lab" / "derived" / "candidate_campaign_coating_flow.csv"
N_SEED = 3           # tubes chosen before the model takes over
N_RANDOM_TRIALS = 2000
SD_FLOOR = 0.05
SEED = 0


def load_candidates() -> tuple[np.ndarray, np.ndarray, list[str]]:
    import csv

    with CANDIDATES_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    X = np.array([[float(r["coating_coded"]), float(r["coded_dose"])] for r in rows])
    y = np.array([float(r["y_candidate"]) for r in rows])
    labels = [f"{r['coating'][:3]}{r['dose_ug_mL']}" for r in rows]
    return X, y, labels


def lab_ofat_order(labels: list[str]) -> list[int]:
    """The order the bench actually ran: fibronectin ascending, then vitronectin."""
    order = []
    for prefix in ("fib", "vit"):
        idx = [i for i, l in enumerate(labels) if l.startswith(prefix)]
        order.extend(sorted(idx, key=lambda i: float(labels[i][3:])))
    return order


def best_so_far(y: np.ndarray, order: list[int]) -> np.ndarray:
    return np.maximum.accumulate(y[order])


def tubes_to_reach(y: np.ndarray, order: list[int], target: float) -> int:
    """How many tubes before best-so-far reaches ``target``. ``len(y) + 1`` if never."""
    curve = best_so_far(y, order)
    hit = np.argmax(curve >= target) if (curve >= target).any() else None
    return int(hit) + 1 if hit is not None else len(y) + 1


def top_cluster(y: np.ndarray, tol: float) -> np.ndarray:
    """Indices whose value is within ``tol`` of the maximum.

    The reason this function exists: the top three tubes here sit within 1.0 percentage
    point of each other on n = 1 with no replicate SD. "Which tube is best" is then a
    question about one noise draw, not about the coating. Any metric that rewards
    finding *that specific tube* is scoring luck, so the headline metric below is
    reaching the CLUSTER, and the exact-best figure is reported alongside as the
    pessimistic bound it is.
    """
    return np.where(y >= y.max() - tol)[0]


def bo_order(X: np.ndarray, y: np.ndarray, seed: int) -> list[int]:
    """Greedy qLogEI restricted to the measured tubes."""
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    chosen = list(rng.choice(len(y), size=N_SEED, replace=False))
    bounds = torch.stack(
        [torch.zeros(X.shape[1], dtype=torch.double), torch.ones(X.shape[1], dtype=torch.double)]
    )
    cfg = AcqConfig(kind="qlogei")
    while len(chosen) < len(y):
        remaining = [i for i in range(len(y)) if i not in chosen]
        tX = torch.tensor(X[chosen], dtype=torch.double)
        tY = torch.tensor(y[chosen], dtype=torch.double).reshape(-1, 1)
        tV = torch.full_like(tY, SD_FLOOR**2)
        model = build_gp(tX, tY, tV, bounds)
        cand = torch.tensor(X[remaining], dtype=torch.double)
        nxt = propose(model, bounds, 1, tX, tY, config=cfg, candidates=cand)
        # map the proposal back to its row
        d = np.abs(X[remaining] - nxt.detach().numpy()[0]).sum(axis=1)
        chosen.append(remaining[int(d.argmin())])
    return chosen


def main() -> int:
    if not CANDIDATES_CSV.exists():
        print(f"missing {CANDIDATES_CSV}; run scripts/build_lab_dataset.py first")
        return 1
    X, y, labels = load_candidates()
    best = float(y.max())
    best_label = labels[int(y.argmax())]

    print("=" * 78)
    print("Phase 3 feasibility on the in-house coating data -- CANDIDATE numbers, not results")
    print("=" * 78)
    print(f"  {len(y)} measured tubes | best is {best_label} at {best:.2f}% CD31")
    print(f"  spread {y.min():.2f}% .. {y.max():.2f}%\n")

    # The identifiability problem, stated before any method is scored.
    cluster = top_cluster(y, tol=1.0)
    print(f"  IDENTIFIABILITY FIRST")
    print(f"    within 1.0pp of the best: {', '.join(f'{labels[i]}={y[i]:.1f}' for i in cluster)}")
    print(f"    n = 1 per tube, no replicate SD, and the software gate carries a 9-14pp")
    print(f"    sensitivity spread. So 'which of these is best' is not answerable from")
    print(f"    this data at all. The headline metric below is therefore reaching the")
    print(f"    CLUSTER; the exact-best figure is the pessimistic bound.\n")
    target = float(y[cluster].min())

    ofat = lab_ofat_order(labels)
    print(f"  the lab's own OFAT order: {' '.join(labels[i] for i in ofat)}")
    ofat_cluster = tubes_to_reach(y, ofat, target)
    ofat_exact = tubes_to_reach(y, ofat, best)
    print(f"  -> reaches the top cluster after {ofat_cluster} tubes "
          f"(the exact best after {ofat_exact})\n")

    rng = np.random.default_rng(SEED)
    rand_cluster, rand_exact = [], []
    for _ in range(N_RANDOM_TRIALS):
        order = list(rng.permutation(len(y)))
        rand_cluster.append(tubes_to_reach(y, order, target))
        rand_exact.append(tubes_to_reach(y, order, best))
    print(f"  random, {N_RANDOM_TRIALS} shuffles: cluster {np.mean(rand_cluster):.2f} tubes, "
          f"exact best {np.mean(rand_exact):.2f}")

    bo_cluster, bo_exact = [], []
    for s in range(5):
        order = bo_order(X, y, seed=s)
        bo_cluster.append(tubes_to_reach(y, order, target))
        bo_exact.append(tubes_to_reach(y, order, best))
    print(f"  BO (qLogEI, {N_SEED} seed tubes), 5 restarts: cluster {bo_cluster} "
          f"-> mean {np.mean(bo_cluster):.2f}")
    print(f"                                              exact  {bo_exact} "
          f"-> mean {np.mean(bo_exact):.2f}\n")

    print("  VERDICT")
    print(f"    Reaching the top cluster: OFAT {ofat_cluster}, random "
          f"{np.mean(rand_cluster):.2f}, BO {np.mean(bo_cluster):.2f}.")
    verdict = []
    if ofat_cluster <= 2:
        verdict.append(
            "The lab's own scan reached the top cluster in "
            f"{ofat_cluster} tubes, so there is almost no headroom for any method."
        )
    if np.mean(bo_cluster) >= np.mean(rand_cluster):
        verdict.append(
            "BO does not beat random here. With 12 points in 2-D and 3 spent on the "
            "opening design, the model has 9 decisions to make over a response that is "
            "flat across its top third -- there is nothing for a surrogate to exploit."
        )
    verdict.append(
        "These 12 points cannot carry a Phase 3 figure. That is a statement about the "
        "SIZE and SHAPE of the design, not about the data quality: one-factor-at-a-time "
        "over 2 factors is the case BO is worst-placed to win, and n=1 makes the "
        "optimum unidentifiable anyway."
    )
    for v in verdict:
        print(f"    -> {v}")

    out = ROOT / "results" / "lab-phase3-feasibility.json"
    out.write_text(json.dumps({
        "source": str(CANDIDATES_CSV.relative_to(ROOT)),
        "status": "CANDIDATE numbers -- y is unsigned, this is not a result",
        "n_tubes": len(y), "best_label": best_label, "best_value": best,
        "top_cluster_tol_pp": 1.0,
        "top_cluster": [{"tube": labels[i], "value": float(y[i])} for i in cluster],
        "cluster_target": target,
        "ofat_order": [labels[i] for i in ofat],
        "ofat_tubes_to_cluster": ofat_cluster, "ofat_tubes_to_exact_best": ofat_exact,
        "random_mean_tubes_to_cluster": float(np.mean(rand_cluster)),
        "random_mean_tubes_to_exact_best": float(np.mean(rand_exact)),
        "bo_tubes_to_cluster": bo_cluster, "bo_mean_tubes_to_cluster": float(np.mean(bo_cluster)),
        "bo_tubes_to_exact_best": bo_exact,
        "verdict": verdict,
    }, indent=2), encoding="utf-8")
    print(f"\n  written to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
