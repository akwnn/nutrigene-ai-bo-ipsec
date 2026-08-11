"""T1.4 — the E2 grid is the artefact every downstream gate anchors to, so it is tracked.

THE DEFECT THESE GUARD
----------------------
`results/e2-grid.json` was gitignored while five scripts and three fidelity gates
anchored to it by path. Two clones therefore held two different E2 runs under the
same filename:

    A's clone   qLogEI mean regret 0.1553   =>  doe - qlogei = -0.0595
    B's clone   qLogEI mean regret 0.1641   =>  doe - qlogei = -0.0708

Both clones' fidelity gates passed, because each compared a regeneration against
its own copy. `q29_symmetric.py` printed `max |delta| 0.000e+00 over 50 rows` in
B's clone; `probe_e2_determinism.py` gets the same verdict in A's. A gate that
compares against an untracked file cannot detect that the file moved with the
clone -- it can only report that a clone agrees with itself.

Q29 read the two numbers as `run_e2.py`'s `report()` disagreeing with its own
stored grid, and asked A to reconcile them before anything was written up.
`report()` was never wrong. `test_the_guard_rejects_the_other_clones_number`
exists so this file demonstrates it can detect the defect rather than asserting
that it would.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "results" / "e2-grid.json"
E2_LOG = ROOT / "results" / "e2.log"
RESULTS_DOC = ROOT / "docs" / "RESULTS-PERSON-A.md"

#: The value B's clone produced. Kept as a literal so the guard below can prove it
#: rejects it -- a regression test that cannot detect the original defect is not one.
OTHER_CLONE_VALUE = -0.0708
PRIMARY = dict(dim=6, sigma=0.25)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True).stdout


def paired_difference(rows, arm: str, cell: dict, ref: str = "qlogei") -> float:
    """`arm` minus `ref`, one number per instance averaged over seeds, then meaned.

    This is `run_e2.report()`'s aggregation, reimplemented rather than imported.
    Importing it would make the log agree with the grid by construction, which is
    the one thing this must not assume.
    """
    sub = [r for r in rows if all(r[k] == v for k, v in cell.items())]
    insts = sorted({r["instance"] for r in sub})
    per = {a: np.array([np.mean([r["regret"] for r in sub
                                 if r["arm"] == a and r["instance"] == i])
                        for i in insts]) for a in (arm, ref)}
    return float((per[arm] - per[ref]).mean())


@pytest.fixture(scope="module")
def grid():
    if not GRID.exists():
        pytest.fail(f"{GRID.relative_to(ROOT)} is missing")
    return json.loads(GRID.read_text())


def test_the_e2_grid_is_tracked_by_git():
    """Untracked, it is not one artefact -- it is one filename per clone."""
    tracked = _git("ls-files", "--", "results/e2-grid.json").strip()
    assert tracked, (
        "results/e2-grid.json is not tracked. Five scripts and three fidelity "
        "gates anchor to it by path, so an untracked copy lets two clones "
        "disagree while both gates pass.")


def test_the_e2_shards_are_tracked_so_the_merge_is_auditable():
    """`e2.log` opens 'merged 1300 rows from 4 shards'. Without them that is a claim."""
    for dim in (6, 8):
        for sigma in ("0.25", "0.1"):
            name = f"results/e2-grid-d{dim}-s{sigma}.json"
            assert _git("ls-files", "--", name).strip(), f"{name} is not tracked"


def test_the_committed_shards_merge_into_the_committed_grid():
    """The merge is reproducible from tracked inputs, not just asserted in a log line."""
    merged = json.loads(GRID.read_text())
    key = lambda r: (r["instance"], r["dim"], r["sigma"], r["seed"], r["arm"])  # noqa: E731
    by_key = {key(r): r for r in merged}
    seen = 0
    for dim in (6, 8):
        for sigma in ("0.25", "0.1"):
            shard = json.loads((ROOT / f"results/e2-grid-d{dim}-s{sigma}.json").read_text())
            for r in shard:
                k = key(r)
                assert k in by_key, f"{k} is in a shard but not in the merged grid"
                for field in ("regret", "best", "auc_post_init"):
                    assert r[field] == pytest.approx(by_key[k][field], abs=0, rel=0), (
                        f"{k} {field}: shard {r[field]} != merged {by_key[k][field]}")
                seen += 1
    assert seen == len(merged), f"shards cover {seen} rows, merged grid has {len(merged)}"


def test_no_tracked_file_contains_merge_conflict_markers():
    """A conflicted artefact preserves a superseded run as if it were a result.

    `results/e2-run1-unfiltered.log` was committed with both sides of a conflict in
    it, which is where the -0.0708 that Q29 cited as an independent recomputation
    actually came from.
    """
    conflicted = []
    for name in _git("ls-files").splitlines():
        p = ROOT / name
        try:
            text = p.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"^<<<<<<< ", text, re.M) and re.search(r"^>>>>>>> ", text, re.M):
            conflicted.append(name)
    assert not conflicted, f"tracked files with unresolved conflict markers: {conflicted}"


def test_e2_log_primary_cell_matches_the_stored_grid(grid):
    """The most-quoted number in the project, checked against the data behind it."""
    printed = re.search(r"^\s+doe:\s+([-+]\d\.\d+)", E2_LOG.read_text(), re.M)
    assert printed, "could not find the primary-cell doe line in results/e2.log"
    assert float(printed.group(1)) == pytest.approx(
        paired_difference(grid, "doe", PRIMARY), abs=5e-5)


def test_results_person_a_headline_matches_the_stored_grid(grid):
    """§1's table is what a reader quotes; it must equal the grid, not the log."""
    row = re.search(r"\|\s*\*\*doe\*\*\s*\|[^|]*\|\s*\*\*(−|-)(\d\.\d+)\*\*",
                    RESULTS_DOC.read_text())
    assert row, "could not find the doe headline row in docs/RESULTS-PERSON-A.md §1"
    assert -float(row.group(2)) == pytest.approx(
        paired_difference(grid, "doe", PRIMARY), abs=5e-5)


def test_the_guard_rejects_the_other_clones_number(grid):
    """Proof the two guards above can fail, using the value that actually diverged."""
    truth = paired_difference(grid, "doe", PRIMARY)
    assert OTHER_CLONE_VALUE != pytest.approx(truth, abs=5e-5), (
        "the guard cannot distinguish A's grid from B's, so it guards nothing")
