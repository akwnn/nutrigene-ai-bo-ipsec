"""Fail-closed, resumable runner for the prospective synthetic EC benchmark.

The production SPADE integration is deliberately a scaffold until the EC campaign
adapter is reviewed.  ``--dry-run`` executes one deterministic mocked campaign and
is the only execution mode exposed by this module; it never launches the full
evaluation.  Truth is used only by the scoring boundary, never to choose points.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import torch

from boec.ec_benchmark import ECConfig, joint_success, make_ec_landscape, registered_ec_families

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "SPADE-EC-BENCHMARK.md"
ARMS = ("spade", "doe", "doe_unscreened", "qlognei")
TRAIN_SEEDS = tuple(range(0, 64))
EVAL_SEEDS = tuple(range(64, 96))
FAMILIES = registered_ec_families()
WELLS = 48
ROUNDS = {"spade": 5, "doe": 3, "doe_unscreened": 3, "qlognei": 5}
REQUIRED_COLUMNS = {
    "family", "seed", "arm", "answer_rate", "containment", "containment_wilson_lower",
    "false_certificate_count", "joint_volume", "point_regret", "adaptive_rounds",
    "training_seed_start", "training_seed_stop", "evaluation_seed_start", "evaluation_seed_stop",
    "spec_sha256", "runner_sha256", "source_commit",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    if trials <= 0:
        return 0.0
    p = successes / trials
    den = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    half = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5)
    return (centre - half) / den


def expected_cells(*, seeds: tuple[int, ...] = EVAL_SEEDS, families: tuple[str, ...] = FAMILIES):
    return {(family, seed, arm) for family in families for seed in seeds for arm in ARMS}


def _provenance() -> dict[str, Any]:
    return {
        "training_seed_start": TRAIN_SEEDS[0], "training_seed_stop": TRAIN_SEEDS[-1] + 1,
        "evaluation_seed_start": EVAL_SEEDS[0], "evaluation_seed_stop": EVAL_SEEDS[-1] + 1,
        "spec_sha256": sha256(SPEC), "runner_sha256": sha256(Path(__file__)),
        "source_commit": source_commit(),
    }


def _mock_row(family: str, seed: int, arm: str) -> dict[str, Any]:
    """One cheap deterministic scaffold row; replace only after adapter review."""
    landscape = make_ec_landscape(family, seed)
    grid = torch.linspace(0.05, 0.95, 8).repeat(6, 1).T
    truth = landscape.truth(grid)
    success = joint_success(truth, torch.tensor(landscape.config.cqa_thresholds))
    # Arms differ only in their deterministic candidate ordering in this scaffold.
    offset = ARMS.index(arm)
    selected = truth[offset::4]
    answered = bool(selected.shape[0] and bool(success[offset::4].any()))
    containment = float(success[offset::4].double().mean()) if answered else 0.0
    optimum = float(truth.max(dim=0).values.mean())
    observed = float(selected.mean()) if selected.numel() else 0.0
    row = {
        "family": family, "seed": seed, "arm": arm,
        "answer_rate": 1.0 if answered else 0.0,
        "containment": containment,
        "containment_wilson_lower": _wilson_lower(int(round(containment * max(1, selected.shape[0]))), max(1, selected.shape[0])),
        "false_certificate_count": 0,
        "joint_volume": containment,
        "point_regret": max(0.0, optimum - observed),
        "adaptive_rounds": ROUNDS[arm],
        **_provenance(),
        "scaffold": True,
    }
    return row


def atomic_write(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(artifact, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def empty_artifact() -> dict[str, Any]:
    return {"status": "PARTIAL", "config": {"wells": WELLS, "spade_rounds": 5, "doe_rounds": 3},
            **_provenance(), "rows": []}


def run(*, out: Path, resume: bool = False, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run:
        raise RuntimeError("full EC evaluation is intentionally disabled; use --dry-run")
    artifact = empty_artifact()
    if resume and out.exists():
        artifact = json.loads(out.read_text(encoding="utf-8"))
        # Refuse to resume an artifact from another protocol before appending rows.
        for key, value in _provenance().items():
            if artifact.get(key) != value:
                raise ValueError(f"cannot resume: provenance mismatch for {key}")
    rows = list(artifact.get("rows", []))
    seen = {(r.get("family"), int(r.get("seed", -1)), r.get("arm")) for r in rows}
    # Exactly one job in dry-run: one family, one evaluation seed, all arms.
    family, seed = FAMILIES[0], EVAL_SEEDS[0]
    for arm in ARMS:
        if (family, seed, arm) not in seen:
            rows.append(_mock_row(family, seed, arm))
            artifact["rows"] = rows
            atomic_write(out, artifact)
    artifact["rows"] = rows
    atomic_write(out, artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "ec-dry-run.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        run(out=args.out, resume=args.resume, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
