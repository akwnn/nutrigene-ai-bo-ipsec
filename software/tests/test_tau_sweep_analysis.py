from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "tau_analysis", ROOT / "software/scripts/analyse_tau_sweep.py"
)
TAU = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(TAU)


def _row(*, seed: int, arm: str, p: float, c: float, margin: float, answered: bool) -> dict:
    return {
        "family": "fixture",
        "seed": seed,
        "arm": arm,
        "p_value": p,
        "inflation_c": c,
        "margin_sd": margin,
        "ce_empty_0.95": not answered,
        "ce_empirical_0.95": True if answered else None,
        "ce_vol_0.95": 0.1 if answered else 0.0,
    }


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "tau-fixture.json"
    path.write_text(json.dumps({"rows": rows}))
    return path


def test_tau1_uses_spade_only_and_means_unique_seed_margins(tmp_path: Path) -> None:
    rows = []
    # qLogNEI deliberately has the opposite answer pattern. Each margin is repeated
    # across arms and c values and must count once in the cell mean.
    for seed, margin in enumerate((1.0, 3.0)):
        for arm in ("spade", "qlognei"):
            for c in (1.0, 1.5):
                rows.append(_row(seed=seed, arm=arm, p=0.7, c=c, margin=margin,
                                 answered=(arm == "spade" and seed == 1)
                                          or (arm == "qlognei" and seed == 0)))

    cells, margins = TAU.load([_write(tmp_path, rows)])
    points = TAU.tau1_points(cells, margins, arm="spade", c=1.0, expected_seed_count=2)

    assert points == [(2.0, 0.5, "fixture", 0.7)]


def test_tau1_is_invariant_to_input_row_reversal(tmp_path: Path) -> None:
    rows = [
        _row(seed=seed, arm=arm, p=p, c=c, margin=margin, answered=answered)
        for seed, margin, answered in ((0, 1.0, False), (1, 3.0, True))
        for arm in ("spade", "qlognei")
        for p in (0.7, 0.5)
        for c in (1.0, 1.5)
    ]
    forward = _write(tmp_path, rows)
    cells_a, margins_a = TAU.load([forward])
    forward.write_text(json.dumps({"rows": list(reversed(rows))}))
    cells_b, margins_b = TAU.load([forward])

    assert TAU.tau1_points(cells_a, margins_a, expected_seed_count=2) == \
        TAU.tau1_points(cells_b, margins_b, expected_seed_count=2)


def test_load_rejects_inconsistent_margin_duplicates(tmp_path: Path) -> None:
    rows = [
        _row(seed=0, arm="spade", p=0.7, c=1.0, margin=1.0, answered=True),
        _row(seed=0, arm="qlognei", p=0.7, c=1.0, margin=1.1, answered=True),
    ]

    with pytest.raises(ValueError, match="inconsistent margin_sd"):
        TAU.load([_write(tmp_path, rows)])


def test_load_rejects_duplicate_cell_key_even_when_identical(tmp_path: Path) -> None:
    row = _row(seed=0, arm="spade", p=0.7, c=1.0, margin=1.0, answered=True)

    with pytest.raises(ValueError, match=r"duplicate TAU cell key.*existing=.*incoming="):
        TAU.load([_write(tmp_path, [row, dict(row)])])


def test_load_rejects_nonfinite_margin(tmp_path: Path) -> None:
    row = _row(seed=0, arm="spade", p=0.7, c=1.0, margin=float("nan"), answered=True)

    with pytest.raises(ValueError, match="non-finite margin_sd"):
        TAU.load([_write(tmp_path, [row])])


def test_tau1_requires_exact_margin_and_answer_seed_alignment(tmp_path: Path) -> None:
    rows = [
        _row(seed=0, arm="spade", p=0.7, c=1.0, margin=1.0, answered=True),
        _row(seed=1, arm="qlognei", p=0.7, c=1.0, margin=2.0, answered=True),
    ]
    cells, margins = TAU.load([_write(tmp_path, rows)])

    with pytest.raises(ValueError, match="seed mismatch"):
        TAU.tau1_points(cells, margins, expected_seed_count=2)


def test_tau1_requires_64_seeds_by_default(tmp_path: Path) -> None:
    rows = [_row(seed=seed, arm="spade", p=0.7, c=1.0, margin=float(seed + 1),
                 answered=True) for seed in range(2)]
    cells, margins = TAU.load([_write(tmp_path, rows)])

    with pytest.raises(ValueError, match="expected 64 seeds"):
        TAU.tau1_points(cells, margins)


def test_tau3_bins_are_invariant_to_input_row_reversal(tmp_path: Path) -> None:
    rows = [
        _row(seed=seed, arm=arm, p=0.7, c=1.0, margin=margin, answered=True)
        | {"ce_vol_0.95": volume}
        for seed, margin in ((0, 0.25), (1, 0.75), (2, 1.5), (3, 2.5))
        for arm, volume in (("spade", seed / 10 + 0.2), ("qlognei", seed / 10 + 0.1))
    ]
    path = _write(tmp_path, rows)
    cells_a, margins_a = TAU.load([path])
    path.write_text(json.dumps({"rows": list(reversed(rows))}))
    cells_b, margins_b = TAU.load([path])

    assert TAU.tau3_bin_differences(cells_a, margins_a) == \
        TAU.tau3_bin_differences(cells_b, margins_b)


def test_canonical_tau_grid_is_complete() -> None:
    paths = [ROOT / "research/results/generalization" / f"tau-{f}.json"
             for f in TAU.FAMILIES]
    cells, margins = TAU.load(paths)

    TAU.validate_canonical(cells, margins)
    assert len(cells) == 5 * 64 * 2 * 5 * 4
    assert len(margins) == 5 * 64 * 5


def test_main_validates_default_canonical_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    class ValidationReached(RuntimeError):
        pass

    def stop_after_validation(cells, margins):
        raise ValidationReached

    monkeypatch.setattr(TAU, "validate_canonical", stop_after_validation)
    monkeypatch.setattr(sys, "argv", ["analyse_tau_sweep.py"])

    with pytest.raises(ValidationReached):
        TAU.main()
