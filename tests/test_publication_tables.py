from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.make_publication_tables import build_tables, write_tables


RESULTS = Path("results")
TARGET = {
    "condition": "hill-d6-s0.1",
    "tau_frac": 0.25,
    "gamma": 0.95,
    "alpha": 0.95,
}


def _copy_sources(destination: Path) -> None:
    for name in (
        "final-spade-c1.json",
        "final-spade-c2.json",
        "final-spade-c3.json",
        "final-spade-c4.json",
        "final-spade-s1.json",
        "final-spade-s2.json",
        "final-spade-s3.json",
        "final-spade-regret-pareto.json",
        "final-spade-kill-ledger.json",
    ):
        shutil.copy2(RESULTS / name, destination / name)


def test_target_calibration_uses_the_registered_cell_and_instance_aggregation():
    tables = build_tables(RESULTS)
    calibration = tables["prospective_calibration"]

    assert {key: calibration[key] for key in TARGET} == TARGET
    assert calibration["unit"] == "n25 landscape instances; campaign seeds averaged within instance"
    assert calibration["lower_is_better"] == [
        "brier",
        "murphy_calibration",
        "symmetric_difference",
        "regret_rule_p",
    ]
    assert len(calibration["rows"]) == 12
    assert calibration["rows"] == sorted(calibration["rows"], key=lambda row: (row["brier"], row["arm"]))

    for row in calibration["rows"]:
        assert row["n_instances"] == 25
        assert row["campaigns_per_instance"] == 4
        for field in (
            "brier",
            "murphy_calibration",
            "murphy_refinement",
            "auc",
            "symmetric_difference",
            "regret_rule_p",
            "wells",
            "rounds",
        ):
            assert field in row


def test_duplicate_identical_campaign_row_does_not_inflate_the_denominator(tmp_path):
    _copy_sources(tmp_path)
    source = json.loads((tmp_path / "final-spade-c2.json").read_text())
    duplicate = next(
        row
        for row in source["rows"]
        if row["arm"] == "spade_cf_m0"
        and row["family"] == "hill"
        and row["dimension"] == 6
        and row["sigma"] == 0.1
        and row["tau_frac_or_quantile"] == 0.25
        and row["gamma"] == 0.95
        and row["alpha"] == 0.95
    )
    source["rows"].append(duplicate)
    (tmp_path / "final-spade-c2.json").write_text(json.dumps(source, allow_nan=True))

    tables = build_tables(tmp_path)
    primary = next(row for row in tables["prospective_calibration"]["rows"] if row["arm"] == "spade_cf_m0")

    assert primary["n_instances"] == 25
    assert primary["campaigns_per_instance"] == 4


def test_conflicting_duplicate_campaign_row_is_rejected(tmp_path):
    _copy_sources(tmp_path)
    source = json.loads((tmp_path / "final-spade-c2.json").read_text())
    duplicate = next(
        row.copy()
        for row in source["rows"]
        if row["arm"] == "spade_cf_m0"
        and row["family"] == "hill"
        and row["dimension"] == 6
        and row["sigma"] == 0.1
        and row["tau_frac_or_quantile"] == 0.25
        and row["gamma"] == 0.95
        and row["alpha"] == 0.95
    )
    duplicate["brier"] += 0.01
    source["rows"].append(duplicate)
    (tmp_path / "final-spade-c2.json").write_text(json.dumps(source, allow_nan=True))

    with pytest.raises(ValueError, match="conflicting duplicate"):
        build_tables(tmp_path)


def test_comparison_and_kill_ledger_preserve_registered_scope():
    tables = build_tables(RESULTS)
    comparison = tables["spade_comparison"]

    assert comparison["primary_terminal_rule"] == "P"
    assert comparison["arms"] == ["doe", "sobol", "qlogei", "qlognei", "spade_cf_m0", "spade_random_plate2"]
    assert len(comparison["rows"]) == 42
    assert {row["condition"] for row in comparison["rows"]} == {
        "ackley-d6-s0.25",
        "hartmann6-d6-s0.25",
        "hartmann6-d8-s0.25",
        "hill-d6-s0.1",
        "hill-d6-s0.25",
        "levy-d6-s0.25",
        "rosenbrock-d6-s0.25",
    }
    assert all(row["wells"] == 48 for row in comparison["rows"])

    ledger = tables["kill_ledger"]
    assert [row["id"] for row in ledger["rows"]] == [f"KF-{index}" for index in range(1, 11)]
    for row in ledger["rows"]:
        assert row["denominator"] not in (None, "", 0)
        for field in ("status", "effect", "ci", "p", "p_adjusted", "sesoi", "interpretation"):
            assert field in row


def test_write_tables_is_deterministic_and_hashes_sources_and_outputs(tmp_path):
    output_dir = tmp_path / "publication-tables"
    expected_names = (
        "publication-tables.json",
        "table-spade-prospective-calibration.csv",
        "table-spade-prospective-calibration.md",
        "table-spade-comparison.csv",
        "table-spade-comparison.md",
        "table-spade-kill-ledger.csv",
        "table-spade-kill-ledger.md",
    )

    written = write_tables(RESULTS, output_dir)
    assert tuple(path.name for path in written) == expected_names
    first = {path.name: path.read_bytes() for path in written}
    assert write_tables(RESULTS, output_dir) == written
    assert {path.name: path.read_bytes() for path in written} == first

    manifest = json.loads((output_dir / "publication-tables.json").read_text())
    assert set(manifest["source_hashes"]) == {
        "final-spade-c1.json",
        "final-spade-c2.json",
        "final-spade-c3.json",
        "final-spade-c4.json",
        "final-spade-s1.json",
        "final-spade-s2.json",
        "final-spade-s3.json",
        "final-spade-regret-pareto.json",
        "final-spade-kill-ledger.json",
    }
    assert set(manifest["output_hashes"]) == set(expected_names[1:])
    for name, digest in manifest["source_hashes"].items():
        assert digest == hashlib.sha256((RESULTS / name).read_bytes()).hexdigest()
    for name, digest in manifest["output_hashes"].items():
        assert digest == hashlib.sha256((output_dir / name).read_bytes()).hexdigest()

    calibration_csv = (output_dir / "table-spade-prospective-calibration.csv").read_text()
    calibration_md = (output_dir / "table-spade-prospective-calibration.md").read_text()
    assert "Brier (lower is better)" in calibration_csv
    assert "Murphy calibration (lower is better)" in calibration_md
    assert "n=25 landscape instances" in calibration_md
    assert "." in calibration_csv
