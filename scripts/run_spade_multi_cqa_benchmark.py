#!/usr/bin/env python3
"""Run the registered scalar-versus-joint synthetic CQA benchmark."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from boec.manufacturing_benchmark import (  # noqa: E402
    BenchmarkConfig,
    aggregate_rows,
    registered_families,
    run_replicate,
)
from boec.seedbook import derive_seed  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "experiment" / "spade-multi-cqa-benchmark.yaml"


def _source_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def _parser(config: dict) -> argparse.ArgumentParser:
    protocol = config["protocol"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="canonical JSON output path")
    parser.add_argument("--replicates", type=int, default=int(protocol["replicates"]))
    parser.add_argument("--algorithm-seeds", type=int, default=int(protocol["algorithm_seeds"]))
    parser.add_argument("--train-count", type=int, default=int(protocol["train_count"]))
    parser.add_argument("--grid-count", type=int, default=int(protocol["grid_count"]))
    parser.add_argument("--families", nargs="+", default=list(config["families"]))
    return parser


def _load_config() -> dict:
    with CONFIG_PATH.open() as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("schema") != "boec-spade-multi-cqa-benchmark-v1":
        raise SystemExit("invalid multi-CQA benchmark configuration schema")
    return config


def main(argv: list[str] | None = None) -> int:
    registration = _load_config()
    args = _parser(registration).parse_args(argv)
    protocol = registration["protocol"]
    if args.replicates < 1 or args.algorithm_seeds < 1:
        raise SystemExit("replicates and algorithm-seeds must be positive")
    if args.train_count < 1 or args.grid_count < 1:
        raise SystemExit("train-count and grid-count must be positive")
    all_families = {family.name: family for family in registered_families(int(protocol["dimension"]))}
    unknown = sorted(set(args.families) - set(all_families))
    if unknown:
        raise SystemExit(f"unknown family/families: {', '.join(unknown)}")
    config = BenchmarkConfig(
        dimension=int(protocol["dimension"]),
        train_count=args.train_count,
        grid_count=args.grid_count,
        n_draws=int(protocol["n_draws"]),
        n_rho=int(protocol["n_rho"]),
        alpha=float(protocol["alpha"]),
        gamma=float(protocol["gamma"]),
        sigma_rel=float(protocol["sigma_rel"]),
        sigma_add=float(protocol["sigma_add"]),
        threshold=float(protocol["threshold"]),
        volume_rule=str(protocol["volume_rule"]),
        latent_inflation=float(protocol.get("latent_inflation", 1.5)),
        mean_marginalisation=bool(protocol.get("mean_marginalisation", True)),
    )
    row_objects = []
    root_seed = 2_026_08_27
    for family_name in args.families:
        family = all_families[family_name]
        for replicate in range(args.replicates):
            replicate_seed = derive_seed(root_seed, "benchmark-replicate", family_name, replicate)
            for algorithm in range(args.algorithm_seeds):
                algorithm_seed = derive_seed(
                    root_seed, "benchmark-algorithm", family_name, replicate, algorithm
                )
                row_objects.append(
                    run_replicate(
                        family,
                        config=config,
                        replicate_seed=replicate_seed,
                        algorithm_seed=algorithm_seed,
                    )
                )
    aggregates = {
        family_name: aggregate_rows(
            [
                row
                for row in row_objects
                if row.family == family_name
            ]
        )
        for family_name in args.families
    }
    output = {
        "schema": registration["schema"],
        "study_id": registration["study_id"],
        "claim_scope": registration["claim_scope"],
        "source_commit": _source_commit(),
        "protocol_digest": config.digest,
        "protocol": {
            **protocol,
            "train_count": args.train_count,
            "grid_count": args.grid_count,
            "replicates": args.replicates,
            "algorithm_seeds": args.algorithm_seeds,
        },
        "families": list(args.families),
        "rows": [row.as_dict() for row in row_objects],
        "aggregate": aggregates,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
