#!/usr/bin/env python3
"""Emit the evidence-backed classification of current historical replay failures.

The observations below come from the focused historical replay command recorded in the
Task 1 report. Content hashes bind every row to the code and committed artifact it audits.
No historical equality gate is changed by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import sys
from typing import Any, Sequence

import botorch
import gpytorch
import numpy as np
import scipy
import torch


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "boec.historical-replay-audit.v1"
CLASSIFICATIONS = frozenset(
    {
        "REPRODUCIBLE_EXACT",
        "REPRODUCIBLE_REGISTERED_TOLERANCE",
        "HISTORICAL_NONREGENERABLE",
    }
)
DEFAULT_ARTIFACT = ROOT / "results" / "historical-replay-audit.json"


OBSERVATIONS: tuple[dict[str, Any], ...] = (
    {
        "gate": "tests/test_d23_doe_subspace.py::test_full_space_rule_p_reproduces_fix1",
        "source_hash": "992eaf996f4ef686b63fffcd17519aeee89fa28622d258f06c09b3e44bf46829",
        "observed_delta": 3.8780535571714125e-07,
        "classification": "HISTORICAL_NONREGENERABLE",
        "registered_tolerance": None,
        "scientific_decision_unchanged": True,
        "selected_point_unchanged": False,
        "evidence": (
            "Rule A and the fixed-grid Rule P regret reproduce exactly, but the continuous "
            "Rule P point changed in every shown coordinate; a tolerance is therefore not "
            "registered despite the small regret delta."
        ),
        "sources": (
            "tests/test_d23_doe_subspace.py",
            "scripts/run_d23_doe_subspace.py",
            "results/fix1-terminal-rule.json",
        ),
    },
    {
        "gate": "tests/test_p4_coord.py::test_k6_scorer_reproduces_a_committed_lhs_row_bitwise",
        "source_hash": "379060c0bca54553978ca8916ad18b1edaf48a13b8108cf84739c7fecc75a1eb",
        "observed_delta": 6.661338147750939e-16,
        "classification": "REPRODUCIBLE_REGISTERED_TOLERANCE",
        "registered_tolerance": 1e-12,
        "scientific_decision_unchanged": True,
        "selected_point_unchanged": True,
        "evidence": (
            "Across all 24 fixed-grid cells, 84 floating fields drifted by at most "
            "6.661e-16 and no discrete field changed. This scorer selects no new point; "
            "its campaign and scoring-grid identities are unchanged."
        ),
        "sources": (
            "tests/test_p4_coord.py",
            "scripts/run_p4_coord.py",
            "src/boec/replay.py",
            "results/k6-designspace-spread.json",
        ),
    },
    {
        "gate": "tests/test_q59_map_rescore.py::test_the_edit_is_additive_and_reproduces_the_committed_columns",
        "source_hash": "3cce0f954f3f481f4a7d45d9540e3c1070ddcdbcf32c95d4a2598b1986cd43b1",
        "observed_delta": 3.1730922445127874e-08,
        "classification": "HISTORICAL_NONREGENERABLE",
        "registered_tolerance": None,
        "scientific_decision_unchanged": True,
        "selected_point_unchanged": False,
        "evidence": (
            "Rule A, oracle-best, design count, and residual degrees of freedom are exact, "
            "but the committed artifact does not retain the Rule C recommendation point. "
            "Point identity cannot be proved, so the exact gate remains non-regenerable."
        ),
        "sources": (
            "tests/test_q59_map_rescore.py",
            "scripts/run_q59_hartmann_no_screen.py",
            "results/q59-hartmann-no-screen.json",
        ),
    },
    {
        "gate": "tests/test_spread_gp.py::test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly",
        "source_hash": "ff0b39c605d08d88e4f4d8698311ebe22f878fd67516ee200a5c334afe794298",
        "observed_delta": 3.122972902502852e-07,
        "classification": "HISTORICAL_NONREGENERABLE",
        "registered_tolerance": None,
        "scientific_decision_unchanged": True,
        "selected_point_unchanged": False,
        "evidence": (
            "The six-row scalar replay drifts by 3.123e-07. The Q52 artifact stores regret "
            "curves but not the posterior-mean recommendation points, so unchanged point "
            "selection cannot be audited and no tolerance is registered."
        ),
        "sources": (
            "tests/test_spread_gp.py",
            "src/boec/spread_gp.py",
            "results/q52-budget-to-target.json",
        ),
    },
    {
        "gate": "tests/test_calibration.py::test_the_checkpoint_write_path_actually_runs",
        "source_hash": "632897af144c2695b3fc2ac82c178cf581cdafb2ca39c798a02a6827bd94a857",
        "observed_delta": 9.082e-13,
        "classification": "REPRODUCIBLE_REGISTERED_TOLERANCE",
        "registered_tolerance": 1e-12,
        "scientific_decision_unchanged": True,
        "selected_point_unchanged": True,
        "evidence": (
            "The fixed-map gate reports 9.082e-13 worst drift while all 24 predictive "
            "rankings, all latent-map cells, and the A5 null verdict remain unchanged. "
            "This analysis selects no new campaign point."
        ),
        "sources": (
            "tests/test_calibration.py",
            "scripts/run_p7_murphy.py",
            "results/k6-designspace-spread.json",
        ),
    },
    {
        "gate": "tests/test_replay.py::test_family_qlogei_reproduces_the_committed_q42_column_exactly",
        "source_hash": "2a80648cb4689b965b97392d3d6ae782329f170878b774e2f63536b37822c37e",
        "observed_delta": 0.033954554533606185,
        "classification": "HISTORICAL_NONREGENERABLE",
        "registered_tolerance": None,
        "scientific_decision_unchanged": False,
        "selected_point_unchanged": False,
        "evidence": (
            "Hartmann6 qLogEI seed 0 regenerates regret 0.19391397009622446 versus "
            "0.22786852462983065 committed. This is a material adaptive trajectory change."
        ),
        "sources": (
            "tests/test_replay.py",
            "src/boec/replay.py",
            "src/boec/optimizers.py",
            "src/boec/campaign.py",
            "src/boec/torch_oracle.py",
            "results/q42-families.json",
        ),
    },
    {
        "gate": "tests/test_replay.py::test_family_qlogei_reproduces_on_every_family_and_at_d8",
        "source_hash": "2a80648cb4689b965b97392d3d6ae782329f170878b774e2f63536b37822c37e",
        "observed_delta": 0.1721093109374322,
        "classification": "HISTORICAL_NONREGENERABLE",
        "registered_tolerance": None,
        "scientific_decision_unchanged": False,
        "selected_point_unchanged": False,
        "evidence": (
            "Ackley qLogEI seed 0 regenerates regret 0.7649100065630514 versus "
            "0.5928006956256192 committed. The mismatch is material, not rounding."
        ),
        "sources": (
            "tests/test_replay.py",
            "src/boec/replay.py",
            "src/boec/optimizers.py",
            "src/boec/campaign.py",
            "src/boec/torch_oracle.py",
            "results/q42-families.json",
        ),
    },
    {
        "gate": "tests/test_replay.py::test_family_qlognei_reproduces_the_q59_hartmann_column",
        "source_hash": "0a081e03895f1edcad612b99661039def986c4dc16fe15aafe4e2fe4007aefb2",
        "observed_delta": 0.02527916780343853,
        "classification": "HISTORICAL_NONREGENERABLE",
        "registered_tolerance": None,
        "scientific_decision_unchanged": False,
        "selected_point_unchanged": False,
        "evidence": (
            "Hartmann6 qLogNEI seed 0 regenerates regret 0.19524908867226243 versus "
            "0.1699699208688239 committed. The adaptive trajectory is non-regenerable."
        ),
        "sources": (
            "tests/test_replay.py",
            "src/boec/replay.py",
            "src/boec/optimizers.py",
            "src/boec/campaign.py",
            "src/boec/torch_oracle.py",
            "results/q59-hartmann-no-screen.json",
        ),
    },
)


def hash_sources(root: Path, sources: Sequence[str]) -> str:
    """Hash path names and bytes so an observation is bound to its audited inputs."""
    root = root.resolve()
    digest = hashlib.sha256()
    for relative in sources:
        path = (root / relative).resolve()
        if path != root and root not in path.parents:
            raise ValueError(f"audit source escapes repository: {relative}")
        if not path.is_file():
            raise FileNotFoundError(path)
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def environment() -> dict[str, Any]:
    """The numerical environment needed to interpret replay differences."""
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "torch": torch.__version__,
        "gpytorch": gpytorch.__version__,
        "botorch": botorch.__version__,
        "threads": {
            "torch": torch.get_num_threads(),
            "torch_interop": torch.get_num_interop_threads(),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
        },
    }


def _validate(observation: dict[str, Any]) -> None:
    classification = observation["classification"]
    if classification not in CLASSIFICATIONS:
        raise ValueError(f"unknown audit classification: {classification}")
    delta = float(observation["observed_delta"])
    tolerance = observation["registered_tolerance"]
    if classification == "REPRODUCIBLE_EXACT" and delta != 0.0:
        raise ValueError("an exact classification requires zero observed delta")
    if classification == "REPRODUCIBLE_REGISTERED_TOLERANCE":
        if not observation["scientific_decision_unchanged"]:
            raise ValueError("tolerance requires an unchanged scientific decision")
        if not observation["selected_point_unchanged"]:
            raise ValueError("tolerance requires unchanged selected-point evidence")
        if tolerance is None or float(tolerance) < delta:
            raise ValueError("registered tolerance must cover the observed delta")
    elif tolerance is not None:
        raise ValueError("only a registered-tolerance classification may carry a tolerance")


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    """Build the deterministic audit document without rerunning expensive campaigns."""
    numerical_environment = environment()
    rows = []
    for observation in OBSERVATIONS:
        _validate(observation)
        sources = list(observation["sources"])
        current_source_hash = hash_sources(root, sources)
        if current_source_hash != observation["source_hash"]:
            raise RuntimeError(
                f"audit observation is stale for {observation['gate']}: "
                f"expected source hash {observation['source_hash']}, "
                f"found {current_source_hash}; rerun the historical gate"
            )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "gate": observation["gate"],
                "observed_delta": observation["observed_delta"],
                "classification": observation["classification"],
                "registered_tolerance": observation["registered_tolerance"],
                "scientific_decision_unchanged": observation[
                    "scientific_decision_unchanged"
                ],
                "selected_point_unchanged": observation["selected_point_unchanged"],
                "evidence": observation["evidence"],
                "environment": numerical_environment,
                "sources": sources,
                "source_hash": observation["source_hash"],
            }
        )
    return {"schema_version": SCHEMA_VERSION, "rows": rows}


def write_audit(path: Path = DEFAULT_ARTIFACT, root: Path = ROOT) -> None:
    """Write an audit document using stable JSON formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_audit(root), indent=2, sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help=f"write JSON to this path (recommended: {DEFAULT_ARTIFACT})",
    )
    args = parser.parse_args(argv)
    if args.output is None:
        json.dump(build_audit(ROOT), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        write_audit(args.output, ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
