#!/usr/bin/env python3
"""Build deterministic paired GitHub Actions matrices for registered SPADE shards.

The pure planning functions in this module never read study outcomes.  Lockbox planning
reads only the committed, canonical POWERED decision to obtain its frozen key-prefix
length; the guarded lockbox runner independently performs the complete validation again.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
POWER_PATH = Path("results/spade-lockbox-power.json")
DEVELOPMENT_FAMILIES = ("hill", "ackley", "hartmann6", "levy", "rosenbrock")
LOCKBOX_FAMILIES = (
    "toroidal_rastrigin",
    "gaussian_basin_mixture",
    "curved_ridge",
    "soft_plateau",
)
DEVELOPMENT_KEYS = 50
MAX_MATRIX_JOBS = 256
MIN_LOCKBOX_KEYS = 350
MAX_LOCKBOX_KEYS = 2000
DEVELOPMENT_SHARD_KEY_SPAN = 4
LOCKBOX_SHARD_KEY_SPAN = 10
SLOTS = ("a", "b", "c", "d")
_SHA_RE = re.compile(r"[0-9a-f]{40}")


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _strict_int(value: object, name: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must lie in {minimum}..{maximum}")
    return value


def _output_path(phase: str, family: str, start: int, stop: int) -> str:
    if phase == "development":
        return f"results/spade-development-{family}-{start:03d}-{stop:03d}.jsonl.gz"
    return f"results/spade-lockbox-{family}-{start:04d}-{stop:04d}.jsonl.gz"


def _units(
    phase: str, sample_size: int | None
) -> list[tuple[str, int, int, str]]:
    if phase == "development":
        if sample_size is not None:
            raise ValueError("development matrix does not accept a sample size")
        families = DEVELOPMENT_FAMILIES
        key_count = DEVELOPMENT_KEYS
        key_span = DEVELOPMENT_SHARD_KEY_SPAN
    elif phase == "lockbox":
        key_count = _strict_int(
            sample_size,
            "lockbox sample size",
            minimum=MIN_LOCKBOX_KEYS,
            maximum=MAX_LOCKBOX_KEYS,
        )
        families = LOCKBOX_FAMILIES
        key_span = LOCKBOX_SHARD_KEY_SPAN
    else:
        raise ValueError("phase must be development or lockbox")
    return [
        (
            family,
            start,
            min(start + key_span, key_count),
            _output_path(
                phase, family, start, min(start + key_span, key_count)
            ),
        )
        for family in families
        for start in range(0, key_count, key_span)
    ]


def _slot(
    label: str, unit: tuple[str, int, int, str] | None
) -> dict[str, object]:
    if unit is None:
        return {
            f"{label}_enabled": False,
            f"{label}_family": "",
            f"{label}_start": 0,
            f"{label}_stop": 0,
            f"{label}_out": "",
        }
    family, start, stop, output = unit
    return {
        f"{label}_enabled": True,
        f"{label}_family": family,
        f"{label}_start": start,
        f"{label}_stop": stop,
        f"{label}_out": output,
    }


def build_jobs(phase: str, *, sample_size: int | None = None) -> list[dict[str, object]]:
    """Pack logical shards while never scheduling over two concurrent processes."""
    units = _units(phase, sample_size)
    jobs: list[dict[str, object]] = []
    if phase == "development":
        # Family-major flattening is deterministic.  Pairing 65 width-4 shards gives
        # 33 runner jobs, filling one max-parallel=40 wave without oversubscribing CPUs.
        for offset in range(0, len(units), 2):
            job: dict[str, object] = {
                "job_id": f"development-{offset // 2:04d}"
            }
            packed = units[offset : offset + 2]
            for index, label in enumerate(SLOTS):
                job.update(_slot(label, packed[index] if index < len(packed) else None))
            jobs.append(job)
    else:
        # One lockbox job owns the same width-10 range across all four families.  The
        # workflow runs a+b, waits, then c+d, preserving a two-process ceiling.
        by_identity = {(unit[0], unit[1]): unit for unit in units}
        assert sample_size is not None
        for start in range(0, sample_size, LOCKBOX_SHARD_KEY_SPAN):
            job = {"job_id": f"lockbox-{start:04d}"}
            packed = [by_identity[(family, start)] for family in LOCKBOX_FAMILIES]
            for index, label in enumerate(SLOTS):
                job.update(_slot(label, packed[index]))
            jobs.append(job)
    validate_exact_coverage(jobs, phase=phase, sample_size=sample_size)
    return jobs


def validate_exact_coverage(
    jobs: Sequence[Mapping[str, object]],
    *,
    phase: str,
    sample_size: int | None,
) -> None:
    """Prove every registered family/key occurs exactly once as a unit range."""
    expected = set(_units(phase, sample_size))
    key_span = (
        DEVELOPMENT_SHARD_KEY_SPAN
        if phase == "development"
        else LOCKBOX_SHARD_KEY_SPAN
    )
    observed: list[tuple[str, int, int, str]] = []
    job_ids: list[str] = []
    for job in jobs:
        job_id = job.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("matrix coverage has an invalid job identity")
        if job.get("a_enabled") is not True:
            raise ValueError("matrix coverage requires an enabled primary slot")
        job_ids.append(job_id)
        for label in SLOTS:
            enabled = job.get(f"{label}_enabled")
            if not isinstance(enabled, bool):
                raise ValueError("matrix coverage has a non-boolean slot gate")
            if not enabled:
                if (
                    job.get(f"{label}_family") != ""
                    or job.get(f"{label}_start") != 0
                    or job.get(f"{label}_stop") != 0
                    or job.get(f"{label}_out") != ""
                ):
                    raise ValueError("matrix coverage disabled slot sentinel drift")
                continue
            family = job.get(f"{label}_family")
            start = job.get(f"{label}_start")
            stop = job.get(f"{label}_stop")
            output = job.get(f"{label}_out")
            if (
                not isinstance(family, str)
                or isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(stop, bool)
                or not isinstance(stop, int)
                or not start < stop <= start + key_span
                or not isinstance(output, str)
            ):
                raise ValueError("matrix coverage contains a malformed registered range")
            observed.append((family, start, stop, output))
    if len(job_ids) != len(set(job_ids)):
        raise ValueError("matrix coverage contains duplicate job identities")
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ValueError("matrix coverage has a gap, overlap, or unregistered range")


def slice_jobs(
    jobs: Sequence[Mapping[str, object]], *, batch_index: object, batch_size: object
) -> dict[str, object]:
    index = _strict_int(batch_index, "batch index", minimum=0, maximum=10**9)
    size = _strict_int(
        batch_size, "batch size", minimum=1, maximum=MAX_MATRIX_JOBS
    )
    total = len(jobs)
    if total == 0:
        raise ValueError("cannot slice an empty matrix")
    total_batches = math.ceil(total / size)
    if index >= total_batches:
        raise ValueError("batch index selects an empty matrix")
    include = [dict(job) for job in jobs[index * size : (index + 1) * size]]
    if not include or len(include) > MAX_MATRIX_JOBS:
        raise ValueError("matrix slice exceeds the 256-job Actions limit")
    return {
        "include": include,
        "total_batches": total_batches,
        "total_jobs": total,
    }


def _load_json_strict(data: bytes) -> object:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"power artifact contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("power artifact is not valid UTF-8 JSON") from exc


def _head_sha(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("cannot resolve source SHA") from exc


def require_source_sha(repo_root: Path, expected_source_sha: str) -> str:
    if _SHA_RE.fullmatch(expected_source_sha) is None:
        raise ValueError("expected source SHA must be 40 lowercase hexadecimal characters")
    actual = _head_sha(repo_root)
    if actual != expected_source_sha:
        raise ValueError("checked-out source SHA differs from the requested source SHA")
    return actual


def load_committed_powered_size(
    repo_root: Path, *, expected_source_sha: str
) -> int:
    """Read only an exact canonical POWERED artifact committed at checkout HEAD."""
    root = repo_root.resolve()
    require_source_sha(root, expected_source_sha)
    path = root / POWER_PATH
    try:
        working_bytes = path.read_bytes()
        committed = subprocess.run(
            ["git", "show", f"HEAD:{POWER_PATH.as_posix()}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("POWERED artifact must exist and be committed at source SHA") from exc
    if working_bytes != committed:
        raise ValueError("working power artifact differs from committed bytes")
    payload = _load_json_strict(working_bytes)
    if canonical_json(payload).encode("utf-8") + b"\n" != working_bytes:
        raise ValueError("committed power artifact is not exact canonical JSON")
    if not isinstance(payload, Mapping):
        raise ValueError("committed power artifact must be a JSON object")
    decision = payload.get("decision")
    if (
        payload.get("schema") != "boec-spade-lockbox-power-v1"
        or payload.get("status") != "POWERED"
        or not isinstance(decision, Mapping)
        or decision.get("status") != "POWERED"
    ):
        raise ValueError("committed lockbox decision must be POWERED")
    n = _strict_int(
        decision.get("selected_sample_size"),
        "selected sample size",
        minimum=MIN_LOCKBOX_KEYS,
        maximum=MAX_LOCKBOX_KEYS,
    )
    if decision.get("selected_instance_prefix") != {
        "first": 0,
        "last": n - 1,
        "count": n,
    }:
        raise ValueError("POWERED decision does not select the exact registered prefix")
    return n


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("development", "lockbox"))
    parser.add_argument("--batch-index", required=True, type=int)
    parser.add_argument("--batch-size", required=True, type=int)
    parser.add_argument("--expected-source-sha")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--github-output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    sample_size = None
    if args.expected_source_sha is not None:
        require_source_sha(args.repo_root, args.expected_source_sha)
    if args.phase == "lockbox":
        if args.expected_source_sha is None:
            raise ValueError("lockbox matrix requires the exact expected source SHA")
        sample_size = load_committed_powered_size(
            args.repo_root, expected_source_sha=args.expected_source_sha
        )
    jobs = build_jobs(args.phase, sample_size=sample_size)
    batch = slice_jobs(
        jobs, batch_index=args.batch_index, batch_size=args.batch_size
    )
    matrix = {"include": batch["include"]}
    with args.github_output.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"matrix={canonical_json(matrix)}\n")
        handle.write(f"total_batches={batch['total_batches']}\n")
        handle.write(f"total_jobs={batch['total_jobs']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
