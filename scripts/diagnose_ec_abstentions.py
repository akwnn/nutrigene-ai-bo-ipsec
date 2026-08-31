"""Training-only attribution of empty EC joint certificates.

This module deliberately never opens the prospective evaluation artifact.  It
rebuilds campaigns for seeds 0..63 with the registered EC runner, then fits the
multi-CQA overlay on those training campaigns and a fresh diagnostic grid.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

import torch

import run_ec_benchmark as runner
from boec.ec_benchmark import CQA_NAMES, ECConfig, make_ec_landscape
from boec.manufacturing_qualification import CqaDefinition, qualify_multi_cqa
from boec.optimizers import sobol_design
from boec.seedbook import derive_seed

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SEEDS = tuple(range(64))
ARMS = tuple(runner.ARMS)
SCHEMA = "spade-ec-abstention-diagnostics-v1"


def source_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _definitions() -> tuple[CqaDefinition, ...]:
    return tuple(CqaDefinition(name=n, units="synthetic_fraction", threshold=t,
        direction="greater_equal", gamma=.95, assay_id=f"synthetic-ec-{n}",
        assay_version="v1", sigma_rel=.04, sigma_add=.01)
        for n, t in zip(CQA_NAMES, (0.70, 0.70, 0.60)))


def classify_abstention(result: Any, *, campaign_joint_hits: int = 0) -> tuple[str, str]:
    """Classify an empty joint result and always return its limiting CQA.

    Endpoint volume zero means that endpoint could not support a reliable set
    (model uncertainty).  Otherwise an empty intersection is a CQA bottleneck;
    when no campaign recipe reaches all CQAs, acquisition coverage is the
    operational limiting factor.  The latter is checked first because it is
    actionable and can coexist with a narrow joint bottleneck.
    """
    if result.status != "ABSTAIN_EMPTY_JOINT":
        raise ValueError("classification requires an abstaining result")
    endpoints = tuple(result.endpoint_results)
    if not endpoints:
        raise ValueError("result has no endpoint results")
    limiting = min(endpoints, key=lambda e: (float(e.volume), e.name)).name
    if campaign_joint_hits == 0 and all(float(e.volume) > 0.0 for e in endpoints):
        return "acquisition_coverage", limiting
    if any(float(e.volume) <= 0.0 for e in endpoints):
        return "model_uncertainty", limiting
    return "joint_cqa_bottleneck", limiting


def diagnose_one(family: str, seed: int, *, arm: str = "spade", test_only: bool = True) -> dict[str, Any] | None:
    """Run one training campaign and return an abstention record, if any."""
    if int(seed) not in TRAIN_SEEDS:
        raise ValueError("diagnostics accept training seeds 0..63 only")
    if arm not in ARMS:
        raise ValueError(f"unknown EC arm {arm!r}")
    campaign = runner._run_arm(family, int(seed), arm, test_only=test_only)
    landscape = make_ec_landscape(family, int(seed), ECConfig())
    Y, Yvar = landscape.evaluate(campaign.X)
    grid = sobol_design(torch.stack((torch.zeros(6), torch.ones(6))),
                        256 if test_only else 2048,
                        seed=derive_seed(seed, "ec-abstention-grid", family, arm))
    truth = landscape.truth(grid)
    truth_joint = (truth >= torch.tensor((.70, .70, .60))).all(dim=1)
    result = qualify_multi_cqa(campaign.X, Y, Yvar,
        torch.stack((torch.zeros(6), torch.ones(6))), _definitions(), grid=grid,
        alpha=.95, n_draws=32 if test_only else 256, n_rho=8 if test_only else 64,
        base_seed=derive_seed(seed, "ec-abstention-fit", family, arm),
        latent_inflation=1.0, mean_marginalisation=True, volume_rule="smallest")
    if result.status != "ABSTAIN_EMPTY_JOINT":
        return None
    campaign_truth = landscape.truth(campaign.X) >= torch.tensor((.70, .70, .60))
    hits = int(campaign_truth.all(dim=1).sum())
    category, limiting = classify_abstention(result, campaign_joint_hits=hits)
    return {"family": family, "seed": int(seed), "arm": arm,
            "classification": category, "limiting_cqa": limiting,
            "status": result.status, "joint_volume": result.joint_volume,
            "endpoint_volumes": {e.name: float(e.volume) for e in result.endpoint_results},
            "campaign_joint_hits": hits, "truth_joint_grid_volume": float(truth_joint.double().mean()),
            "alpha": result.alpha, "alpha_endpoint": result.alpha_endpoint,
            "base_seed": result.base_seed, "execution_mode": "TRAINING_ONLY",
            "training_seed_start": 0, "training_seed_stop": 64,
            "source_commit": source_commit()}


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def run(*, out: Path, family: str, arm: str = "spade", seeds: tuple[int, ...] = TRAIN_SEEDS,
        dry_run: bool = False) -> dict[str, Any]:
    if any(s not in TRAIN_SEEDS for s in seeds):
        raise ValueError("diagnostics accept training seeds 0..63 only")
    selected = seeds[:1] if dry_run else seeds
    artifact: dict[str, Any] = {"schema": SCHEMA, "status": "PARTIAL", "family": family,
        "arm": arm, "training_seeds": list(selected), "evaluation_seeds": [], "rows": [],
        "source_commit": source_commit()}
    for seed in selected:
        row = diagnose_one(family, seed, arm=arm, test_only=dry_run)
        if row is not None: artifact["rows"].append(row)
        atomic_write(out, artifact)
    artifact["status"] = "COMPLETE"
    atomic_write(out, artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=runner.FAMILIES, default=runner.FAMILIES[0])
    parser.add_argument("--arm", choices=ARMS, default="spade")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "ec-abstention-diagnostics.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(out=args.out, family=args.family, arm=args.arm, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
