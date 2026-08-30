from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch

from boec.manufacturing_benchmark import (
    BenchmarkConfig,
    aggregate_rows,
    evaluate_family,
    registered_families,
    run_replicate,
)


ROOT = Path(__file__).resolve().parents[1]


def smoke_config() -> BenchmarkConfig:
    return BenchmarkConfig(
        dimension=6,
        train_count=12,
        grid_count=48,
        n_draws=16,
        n_rho=8,
        alpha=0.95,
        gamma=0.95,
        sigma_rel=0.04,
        sigma_add=0.01,
        threshold=0.50,
        volume_rule="smallest",
    )


def test_registered_families_are_bounded_and_deterministic():
    families = registered_families()
    assert [family.name for family in families] == [
        "aligned",
        "moderate_conflict",
        "strong_conflict",
    ]
    X = torch.rand(7, 6, dtype=torch.double)
    for family in families:
        first = evaluate_family(family, X)
        second = evaluate_family(family, X)
        assert first.shape == (7, 3)
        assert torch.equal(first, second)
        assert bool(torch.all((first >= 0) & (first <= 1)))


def test_family_evaluation_rejects_wrong_dimension():
    with pytest.raises(ValueError, match="dimension"):
        evaluate_family(registered_families()[0], torch.zeros(3, 5, dtype=torch.double))


def test_one_smoke_replicate_reports_scalar_and_joint_metrics():
    row = run_replicate(
        registered_families()[0], config=smoke_config(), replicate_seed=3, algorithm_seed=7
    )
    payload = row.as_dict()
    assert payload["family"] == "aligned"
    assert payload["scalar_primary_volume"] >= 0.0
    assert payload["joint_volume"] >= 0.0
    assert payload["joint_status"] in {"QUALIFIED", "ABSTAIN_EMPTY_JOINT"}
    assert len(payload["endpoint_volumes"]) == 3
    assert payload["scalar_unsafe_rate"] is None or 0.0 <= payload["scalar_unsafe_rate"] <= 1.0


def test_replicate_is_deterministic_and_aggregate_does_not_pool_grid_points():
    family = registered_families()[1]
    config = smoke_config()
    first = run_replicate(family, config=config, replicate_seed=4, algorithm_seed=8)
    second = run_replicate(family, config=config, replicate_seed=4, algorithm_seed=8)
    assert first.as_dict() == second.as_dict()
    aggregate = aggregate_rows([first, second])
    assert aggregate["replicate_count"] == 2
    assert aggregate["grid_points_pooled"] is False
    assert "median_joint_volume" in aggregate


def test_strong_conflict_empty_unsafe_rate_is_json_null():
    row = run_replicate(
        registered_families()[2], config=smoke_config(), replicate_seed=5, algorithm_seed=9
    )
    payload = row.as_dict()
    if payload["joint_status"] == "ABSTAIN_EMPTY_JOINT":
        assert payload["joint_unsafe_rate"] is None
    json.dumps(payload, allow_nan=False)


def test_registered_benchmark_configuration_is_explicit():
    import yaml

    path = ROOT / "configs" / "experiment" / "spade-multi-cqa-benchmark.yaml"
    config = yaml.safe_load(path.read_text())
    assert config["protocol"]["train_count"] == 48
    assert config["protocol"]["grid_count"] == 4096
    assert config["protocol"]["replicates"] == 25
    assert config["protocol"]["algorithm_seeds"] == 2
    assert float(config["protocol"]["alpha"]) == 0.95
    assert float(config["protocol"]["gamma"]) == 0.95
    assert float(config["protocol"]["latent_inflation"]) == 1.5
    assert config["protocol"]["mean_marginalisation"] is True
    assert config["families"] == ["aligned", "moderate_conflict", "strong_conflict"]


def test_runner_emits_reproducible_canonical_json(tmp_path):
    script = ROOT / "scripts" / "run_spade_multi_cqa_benchmark.py"
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    command = [
        sys.executable,
        str(script),
        "--out",
        str(first_path),
        "--replicates",
        "1",
        "--algorithm-seeds",
        "1",
        "--families",
        "aligned",
        "--train-count",
        "8",
        "--grid-count",
        "16",
    ]
    first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    command[3] = str(second_path)
    second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert second.returncode == 0, second.stderr
    first_json = json.loads(first_path.read_text())
    second_json = json.loads(second_path.read_text())
    assert first_json == second_json
    assert first_json["schema"] == "boec-spade-multi-cqa-benchmark-v1"
    assert len(first_json["rows"]) == 1
    json.dumps(first_json, allow_nan=False)
