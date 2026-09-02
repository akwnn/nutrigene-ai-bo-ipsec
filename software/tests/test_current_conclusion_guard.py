from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_conclusion_guard_uses_superseding_dc_parity_result() -> None:
    completed = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "software/scripts/verify_conclusions.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "DC one-process SPADE R=5 vs qLogNEI R=10" in completed.stdout
    assert "doc=-0.0005  recomputed=-0.000510" in completed.stdout
    assert "research/results/comparisons/dc-*.json" in completed.stdout


def test_conclusion_guard_rejects_stale_lc_volume_number() -> None:
    completed = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "software/scripts/verify_conclusions.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "CLAIM 3 -- matched-round certified volume" in completed.stdout
    assert "doc=0.0008546875  recomputed=0.000855" in completed.stdout
    assert "n: doc=320" in completed.stdout
    assert "0.001353" not in completed.stdout
