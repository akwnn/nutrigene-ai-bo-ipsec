"""Deterministically audit when TT's target can affect acquisition rankings."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_tt_theta_tau as tt

FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")
SEED_START = 0
SEED_STOP = 32
ADAPTIVE_ROUNDS = 4
JOSEPH_SOURCE_COMMIT = "9d88dc454e85396db64d531a4b044a9ca1ddca18"
SPEC = ROOT / "docs" / "SPADE-THETA-TAU-SPEC.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def validate_rows(rows: list[dict], families, seeds, adaptive_rounds: int) -> None:
    expected = {
        (family, int(seed), round_index)
        for family in families
        for seed in seeds
        for round_index in range(1, adaptive_rounds + 1)
    }
    seen: set[tuple[str, int, int]] = set()
    for row in rows:
        key = (str(row["family"]), int(row["seed"]), int(row["adaptive_round"]))
        if key in seen:
            raise ValueError(f"duplicate TT activation cell: {key}")
        seen.add(key)
    missing = expected - seen
    extra = seen - expected
    if missing:
        raise ValueError(f"missing TT activation cells: {sorted(missing)[:5]}")
    if extra:
        raise ValueError(f"unexpected TT activation cells: {sorted(extra)[:5]}")


def summarize_rows(rows: list[dict], families, seeds, adaptive_rounds: int) -> dict:
    families = tuple(families)
    seeds = tuple(int(seed) for seed in seeds)
    validate_rows(rows, families, seeds, adaptive_rounds)
    by_key = {
        (str(row["family"]), int(row["seed"]), int(row["adaptive_round"])):
        bool(row["active"])
        for row in rows
    }
    by_family = {}
    for family in families:
        counts = [
            sum(by_key[(family, seed, round_index)] for seed in seeds)
            for round_index in range(1, adaptive_rounds + 1)
        ]
        fully_active = sum(
            all(by_key[(family, seed, round_index)]
                for round_index in range(1, adaptive_rounds + 1))
            for seed in seeds
        )
        by_family[family] = {
            "active_by_round": counts,
            "campaigns_active_all_rounds": fully_active,
        }
    return {
        "active_rounds": sum(bool(row["active"]) for row in rows),
        "total_rounds": len(rows),
        "campaigns_active_all_rounds": sum(
            item["campaigns_active_all_rounds"] for item in by_family.values()
        ),
        "total_campaigns": len(families) * len(seeds),
        "by_family": by_family,
    }


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def run_audit(families, seed_start: int, seed_stop: int) -> list[dict]:
    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid

    lc = tt.lc()
    protocol = lc.kv().p8()
    p2 = protocol.p2()
    grid = sobol_grid(protocol.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    tau_cache: dict[str, float] = {}
    rows: list[dict] = []

    for family in families:
        for seed in range(seed_start, seed_stop):
            instance = lc.instance_for(family, seed)
            if instance not in tau_cache:
                with torch.no_grad():
                    truth = protocol.evaluator_for(family, instance, 0).truth(grid)
                tau_cache[instance] = float(tau_quantile(truth.reshape(-1).double(),
                                                         tt.TARGET_P))
            activation_log: list[bool] = []
            tt.build(family, "spade_tau", seed, 5, tau_cache[instance],
                     activation_log=activation_log)
            if len(activation_log) != ADAPTIVE_ROUNDS:
                raise RuntimeError(
                    f"{family} seed {seed}: expected {ADAPTIVE_ROUNDS} adaptive rounds, "
                    f"recorded {len(activation_log)}"
                )
            rows.extend(
                {
                    "family": family,
                    "seed": seed,
                    "adaptive_round": round_index,
                    "active": active,
                }
                for round_index, active in enumerate(activation_log, start=1)
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "tt-activation-audit.json")
    parser.add_argument("--seed-start", type=int, default=SEED_START)
    parser.add_argument("--seed-stop", type=int, default=SEED_STOP)
    parser.add_argument("--families", default=",".join(FAMILIES))
    args = parser.parse_args()

    families = tuple(part.strip() for part in args.families.split(",") if part.strip())
    seeds = range(args.seed_start, args.seed_stop)
    rows = run_audit(families, args.seed_start, args.seed_stop)
    summary = summarize_rows(rows, families, seeds, ADAPTIVE_ROUNDS)
    payload = {
        "status": "COMPLETE",
        "source_commit": _git("rev-parse", "HEAD"),
        "source_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "joseph_source_commit": JOSEPH_SOURCE_COMMIT,
        "spec_sha256": _sha256(SPEC),
        "script_sha256": _sha256(Path(__file__)),
        "families": list(families),
        "seed_start": args.seed_start,
        "seed_stop": args.seed_stop,
        "adaptive_rounds": ADAPTIVE_ROUNDS,
        **summary,
        "rows": rows,
    }
    _atomic_json(args.out, payload)
    print(json.dumps({key: payload[key] for key in (
        "active_rounds", "total_rounds", "campaigns_active_all_rounds",
        "total_campaigns", "by_family")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
