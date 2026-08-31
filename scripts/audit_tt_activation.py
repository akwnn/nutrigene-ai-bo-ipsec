"""Reproduce and audit activation of the registered TT target contour.

This intentionally reruns only the design/model path; it never reads or rewrites the
immutable ``results/tt-*.json`` evidence.  Activation is defined by the production
predicate in :mod:`boec.certstraddle` and is evaluated on each round's exact candidate
grid before the adaptive batch is selected.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")
SEED_START, SEED_STOP, ADAPTIVE_ROUNDS = 0, 32, 4
SOURCE_COMMIT = "9d88dc454e85396db64d531a4b044a9ca1ddca18"
THETA_RHO = 0.95
BUDGET, QBATCH = 48, 8


def _load_runner():
    path = ROOT / "scripts" / "run_lc_confirmatory.py"
    spec = importlib.util.spec_from_file_location("tt_activation_lc", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit() -> dict:
    sys.path.insert(0, str(ROOT / "src"))
    from boec.certstraddle import batch_lse_rho, contour_target_is_active, rho_contour_offset
    from boec.designspace import gp_adapter, tau_quantile
    from boec.norms import sobol_grid
    from boec.lse import exclusion_radius
    from boec.replay import unit_bounds
    from boec.runner import static_design
    from boec.surrogate import build_gp
    from boec.multiround import round_schedule

    runner = _load_runner()
    params = runner.kv().p8()
    z_rho = rho_contour_offset(THETA_RHO)
    n_init, batches = round_schedule(BUDGET, 5, BUDGET - QBATCH * 4)
    assert len(batches) == ADAPTIVE_ROUNDS
    grid = sobol_grid(params.DIM, params.p2().GRID_N, seed=params.p2().GRID_SEED)
    tau_cache = {}
    per_family_round = {family: [0] * ADAPTIVE_ROUNDS for family in FAMILIES}
    records = []

    for family in FAMILIES:
        for seed in range(SEED_START, SEED_STOP):
            instance = runner.instance_for(family, seed)
            if instance not in tau_cache:
                with torch.no_grad():
                    truth = params.evaluator_for(family, instance, 0).truth(grid).reshape(-1).double()
                tau_cache[instance] = float(tau_quantile(truth, 0.30))
            theta = tau_cache[instance]
            orc = params.evaluator_for(family, instance, seed)
            bounds = unit_bounds(params.DIM)
            X = static_design(bounds, "lhs", n_init, seed)
            Y, Yvar = orc.evaluate(X)
            for round_index, q in enumerate(batches):
                model = build_gp(X, Y, Yvar, bounds)
                candidate = sobol_grid(params.DIM, 2000, seed=seed * 131 + round_index)
                with torch.no_grad():
                    mean, sd = gp_adapter(model).posterior_mean_and_sd(candidate)
                    adjusted = mean - z_rho * sd
                    active = contour_target_is_active(adjusted, theta)
                if active:
                    per_family_round[family][round_index] += 1
                records.append({"family": family, "seed": seed, "round": round_index + 1,
                                "theta": theta, "rho": THETA_RHO,
                                "active": bool(active)})
                Xq = batch_lse_rho(gp_adapter(model), candidate, theta, int(q),
                                   exclude=exclusion_radius(model), rho=THETA_RHO)
                Yq, Vq = orc.evaluate(Xq)
                X = torch.cat([X, Xq]); Y = torch.cat([Y, Yq]); Yvar = torch.cat([Yvar, Vq])
                del model, candidate

    active_rounds = sum(per_family_round[family][r] for family in FAMILIES for r in range(ADAPTIVE_ROUNDS))
    active_all = sum(all(row["active"] for row in records if row["family"] == family and row["seed"] == seed)
                     for family in FAMILIES for seed in range(SEED_START, SEED_STOP))
    return {
        "status": "COMPLETE",
        "source_commit": SOURCE_COMMIT,
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "tt_spec_sha256": _sha256(ROOT / "docs" / "SPADE-THETA-TAU-SPEC.md"),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "families": list(FAMILIES), "seed_start": SEED_START, "seed_stop": SEED_STOP,
        "adaptive_rounds": ADAPTIVE_ROUNDS, "active_rounds": active_rounds,
        "total_rounds": len(records), "campaigns_active_all_rounds": active_all,
        "total_campaigns": len(FAMILIES) * (SEED_STOP - SEED_START),
        "active_by_family_round": per_family_round, "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "tt-activation-audit.json")
    args = parser.parse_args()
    result = audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=args.out.parent, prefix=f".{args.out.name}.",
                                     suffix=".tmp", delete=False) as tmp:
        json.dump(result, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        temporary = Path(tmp.name)
    temporary.replace(args.out)
    for family in FAMILIES:
        print(f"{family}: {result['active_by_family_round'][family]}")
    print(f"active rounds: {result['active_rounds']}/{result['total_rounds']}")
    print(f"campaigns active all rounds: {result['campaigns_active_all_rounds']}/{result['total_campaigns']}")


if __name__ == "__main__":
    main()
