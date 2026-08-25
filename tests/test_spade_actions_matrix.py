from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import make_spade_actions_matrix as matrix


DEVELOPMENT_FAMILIES = ("hill", "ackley", "hartmann6", "levy", "rosenbrock")
LOCKBOX_FAMILIES = (
    "toroidal_rastrigin",
    "gaussian_basin_mixture",
    "curved_ridge",
    "soft_plateau",
)


SLOTS = ("a", "b", "c", "d")


def _flatten(jobs: list[dict[str, object]]) -> list[tuple[str, int, int, str]]:
    units: list[tuple[str, int, int, str]] = []
    for job in jobs:
        for slot in SLOTS:
            if job[f"{slot}_enabled"]:
                units.append(
                    (
                        str(job[f"{slot}_family"]),
                        int(job[f"{slot}_start"]),
                        int(job[f"{slot}_stop"]),
                        str(job[f"{slot}_out"]),
                    )
                )
    return units


def _assert_exact_coverage(
    units: list[tuple[str, int, int, str]],
    families: tuple[str, ...],
    stop: int,
) -> None:
    width = 4 if families == DEVELOPMENT_FAMILIES else 10
    expected_ranges = [(start, min(start + width, stop)) for start in range(0, stop, width)]
    assert len(units) == len(families) * len(expected_ranges)
    assert len(set(units)) == len(units)
    for family in families:
        intervals = sorted((start, end) for got, start, end, _ in units if got == family)
        assert intervals == expected_ranges


def test_development_plan_pairs_sixty_five_four_key_shards_into_one_wave() -> None:
    jobs = matrix.build_jobs("development")

    assert len(jobs) == 33
    assert all(job["a_enabled"] for job in jobs)
    assert sum(bool(job["b_enabled"]) for job in jobs) == 32
    assert all(not job[f"{slot}_enabled"] for job in jobs for slot in ("c", "d"))
    units = _flatten(jobs)
    _assert_exact_coverage(units, DEVELOPMENT_FAMILIES, 50)
    assert units[0] == (
        "hill",
        0,
        4,
        "results/spade-development-hill-000-004.jsonl.gz",
    )
    assert units[-1] == (
        "rosenbrock",
        48,
        50,
        "results/spade-development-rosenbrock-048-050.jsonl.gz",
    )
    matrix.validate_exact_coverage(jobs, phase="development", sample_size=None)


def test_lockbox_plan_uses_powered_prefix_and_slices_below_matrix_limit() -> None:
    jobs = matrix.build_jobs("lockbox", sample_size=350)

    assert len(jobs) == 35
    assert all(
        all(job[f"{slot}_enabled"] for slot in ("a", "b", "c", "d"))
        for job in jobs
    )
    units = _flatten(jobs)
    _assert_exact_coverage(units, LOCKBOX_FAMILIES, 350)
    assert units[0][3] == (
        "results/spade-lockbox-toroidal_rastrigin-0000-0010.jsonl.gz"
    )
    assert units[-1][3] == "results/spade-lockbox-soft_plateau-0340-0350.jsonl.gz"
    matrix.validate_exact_coverage(jobs, phase="lockbox", sample_size=350)

    batches = [
        matrix.slice_jobs(jobs, batch_index=index, batch_size=16)
        for index in range(3)
    ]
    assert [len(batch["include"]) for batch in batches] == [16, 16, 3]
    assert [batch["total_batches"] for batch in batches] == [3, 3, 3]
    assert [batch["total_jobs"] for batch in batches] == [35, 35, 35]
    assert sum((batch["include"] for batch in batches), []) == jobs


@pytest.mark.parametrize(
    ("sample_size", "expected_jobs", "last_start"),
    [(351, 36, 350), (2000, 200, 1990)],
)
def test_lockbox_packing_handles_partial_tail_and_registered_maximum(
    sample_size: int, expected_jobs: int, last_start: int
) -> None:
    jobs = matrix.build_jobs("lockbox", sample_size=sample_size)

    assert len(jobs) == expected_jobs <= 256
    assert jobs[-1]["a_start"] == last_start
    assert jobs[-1]["a_stop"] == sample_size
    matrix.validate_exact_coverage(
        jobs, phase="lockbox", sample_size=sample_size
    )


@pytest.mark.parametrize(
    ("batch_index", "batch_size"),
    [(-1, 256), (0, 0), (0, 257), (3, 256), (True, 256)],
)
def test_batch_slice_rejects_invalid_or_empty_requests(
    batch_index: object, batch_size: object
) -> None:
    with pytest.raises(ValueError):
        matrix.slice_jobs(
            matrix.build_jobs("lockbox", sample_size=350),
            batch_index=batch_index,
            batch_size=batch_size,
        )


def test_coverage_validator_detects_gap_overlap_and_non_unit_range() -> None:
    jobs = matrix.build_jobs("development")
    jobs[0] = {**jobs[0], "a_start": 1, "a_stop": 10}

    with pytest.raises(ValueError, match="coverage"):
        matrix.validate_exact_coverage(
            jobs, phase="development", sample_size=None
        )


def test_coverage_validator_rejects_hidden_data_in_disabled_slot() -> None:
    jobs = matrix.build_jobs("development")
    assert not jobs[-1]["b_enabled"]
    jobs[-1] = {**jobs[-1], "b_out": "results/unregistered.jsonl.gz"}

    with pytest.raises(ValueError, match="disabled slot"):
        matrix.validate_exact_coverage(
            jobs, phase="development", sample_size=None
        )


def _init_power_repo(tmp_path: Path, *, status: str = "POWERED", n: int = 350) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    (repo / "results").mkdir(parents=True)
    selected = n if status == "POWERED" else None
    prefix = {"first": 0, "last": n - 1, "count": n} if selected else None
    payload = {
        "schema": "boec-spade-lockbox-power-v1",
        "status": status,
        "decision": {
            "status": status,
            "selected_sample_size": selected,
            "selected_instance_prefix": prefix,
        },
    }
    power = repo / "results" / "spade-lockbox-power.json"
    power.write_text(matrix.canonical_json(payload) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "freeze power"], cwd=repo, check=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo, sha


def test_lockbox_size_requires_exact_committed_powered_artifact(tmp_path: Path) -> None:
    repo, sha = _init_power_repo(tmp_path)

    assert matrix.load_committed_powered_size(repo, expected_source_sha=sha) == 350

    power = repo / "results" / "spade-lockbox-power.json"
    payload = json.loads(power.read_text())
    payload["decision"]["selected_sample_size"] = 351
    power.write_text(matrix.canonical_json(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="committed"):
        matrix.load_committed_powered_size(repo, expected_source_sha=sha)


def test_lockbox_size_refuses_wrong_source_and_unpowered_decision(tmp_path: Path) -> None:
    repo, sha = _init_power_repo(tmp_path / "powered")
    with pytest.raises(ValueError, match="source SHA"):
        matrix.load_committed_powered_size(repo, expected_source_sha="0" * 40)

    unpowered, unpowered_sha = _init_power_repo(
        tmp_path / "unpowered", status="INSUFFICIENT_POWER"
    )
    with pytest.raises(ValueError, match="POWERED"):
        matrix.load_committed_powered_size(
            unpowered, expected_source_sha=unpowered_sha
        )


def test_cli_is_deterministic_and_writes_compact_github_outputs(tmp_path: Path) -> None:
    output = tmp_path / "github-output"
    command = [
        sys.executable,
        "scripts/make_spade_actions_matrix.py",
        "--phase",
        "development",
        "--batch-index",
        "0",
        "--batch-size",
        "256",
        "--github-output",
        str(output),
    ]
    first = subprocess.run(command, check=True, capture_output=True, text=True)
    first_outputs = output.read_text(encoding="utf-8")
    output.unlink()
    second = subprocess.run(command, check=True, capture_output=True, text=True)

    assert first.stdout == second.stdout == ""
    assert output.read_text(encoding="utf-8") == first_outputs
    lines = dict(line.split("=", 1) for line in first_outputs.splitlines())
    assert len(json.loads(lines["matrix"])["include"]) == 33
    assert lines["total_batches"] == "1"
    assert lines["total_jobs"] == "33"


def test_worker_preflight_enforces_cpu_single_thread_runtime() -> None:
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONHASHSEED": "0",
        "CUDA_VISIBLE_DEVICES": "",
    }
    result = subprocess.run(
        [sys.executable, "scripts/run_spade_actions_worker.py", "--preflight"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "cuda_available": False,
        "torch_interop_threads": 1,
        "torch_threads": 1,
    }


def test_worker_preflight_rejects_missing_thread_freeze() -> None:
    env = {**os.environ, "OMP_NUM_THREADS": "2"}
    result = subprocess.run(
        [sys.executable, "scripts/run_spade_actions_worker.py", "--preflight"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "OMP_NUM_THREADS must equal 1" in result.stderr
