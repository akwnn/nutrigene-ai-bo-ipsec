from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_conclusion_guard_uses_superseding_dc_parity_result() -> None:
    completed = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "scripts/verify_conclusions.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "DC one-process SPADE R=5 vs qLogNEI R=10" in completed.stdout
    assert "doc=-0.0005  recomputed=-0.000510" in completed.stdout
    assert "results/dc-*.json" in completed.stdout
