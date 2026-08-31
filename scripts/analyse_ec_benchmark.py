"""Fail-closed validation and summary for EC benchmark artifacts."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from run_ec_benchmark import ARMS, EVAL_SEEDS, FAMILIES, REQUIRED_COLUMNS, TRAIN_SEEDS, expected_cells, sha256, SPEC, source_commit


def validate_artifact(path: Path) -> None:
    """Refuse incomplete, duplicated, non-finite, or provenance-drifted artifacts."""
    artifact: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    if artifact.get("status") != "COMPLETE":
        raise ValueError("artifact is not COMPLETE")
    if artifact.get("spec_sha256") != sha256(SPEC):
        raise ValueError("spec digest mismatch")
    runner = Path(__file__).with_name("run_ec_benchmark.py")
    if artifact.get("runner_sha256") != sha256(runner):
        raise ValueError("runner digest mismatch")
    if artifact.get("training_seed_start") != TRAIN_SEEDS[0] or artifact.get("training_seed_stop") != TRAIN_SEEDS[-1] + 1:
        raise ValueError("training seed bounds mismatch")
    if artifact.get("evaluation_seed_start") != EVAL_SEEDS[0] or artifact.get("evaluation_seed_stop") != EVAL_SEEDS[-1] + 1:
        raise ValueError("evaluation seed bounds mismatch")
    if artifact.get("source_commit") != source_commit():
        raise ValueError("source commit mismatch")
    if set(TRAIN_SEEDS) & set(EVAL_SEEDS):
        raise ValueError("training and evaluation seeds overlap")
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != len(expected_cells()):
        raise ValueError("partial or wrong-size grid")
    seen = set()
    for row in rows:
        missing = REQUIRED_COLUMNS - set(row)
        if missing: raise ValueError(f"missing columns: {sorted(missing)}")
        key = (row["family"], int(row["seed"]), row["arm"])
        if key in seen: raise ValueError(f"duplicate cell {key}")
        if key not in expected_cells(): raise ValueError(f"unexpected cell {key}")
        seen.add(key)
        for name in ("answer_rate", "containment", "containment_wilson_lower", "false_certificate_count", "joint_volume", "point_regret", "adaptive_rounds"):
            if not math.isfinite(float(row[name])): raise ValueError(f"non-finite {name}")
        for name in ("spec_sha256", "runner_sha256", "source_commit"):
            if row[name] != artifact[name]: raise ValueError(f"row provenance mismatch: {name}")
    if seen != expected_cells(): raise ValueError("missing grid cells")


def analyse(path: Path) -> dict[str, Any]:
    validate_artifact(path)
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("artifact", type=Path)
    try:
        analyse(parser.parse_args().artifact)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__": sys.exit(main())
