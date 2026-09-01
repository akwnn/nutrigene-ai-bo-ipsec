from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "6e4f22e"


def _git(*args: str) -> list[str]:
    output = subprocess.check_output(["git", *args], cwd=ROOT, text=True)
    return output.splitlines()


def _rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_baseline_commit_count_is_frozen() -> None:
    assert _git("rev-list", "--count", BASELINE) == ["719"]


def test_file_review_has_one_unique_row_per_baseline_file() -> None:
    tracked = _git("ls-tree", "-r", "--name-only", BASELINE)
    rows = _rows("paper-evidence/file-review.csv")
    paths = [row["baseline_path"] for row in rows]

    assert len(paths) == len(tracked)
    assert len(paths) == len(set(paths))
    assert sorted(paths) == sorted(tracked)


def test_commit_review_has_one_unique_row_per_baseline_commit() -> None:
    commits = _git("rev-list", BASELINE)
    rows = _rows("paper-evidence/commit-review.csv")
    hashes = [row["commit"] for row in rows]

    assert len(hashes) == 719
    assert len(hashes) == len(set(hashes))
    assert set(hashes) == set(commits)


def test_inventory_rows_have_required_headers() -> None:
    file_rows = _rows("paper-evidence/file-review.csv")
    commit_rows = _rows("paper-evidence/commit-review.csv")

    assert file_rows
    assert commit_rows
    assert set(file_rows[0]) == {
        "baseline_path",
        "file_type",
        "first_commit",
        "latest_meaningful_commit",
        "research_era",
        "scientific_question",
        "evidence_level",
        "manuscript_claim",
        "reproduction_role",
        "dependencies",
        "supersession_status",
        "classification",
        "destination",
        "rationale",
    }
    assert set(commit_rows[0]) == {
        "commit",
        "date",
        "subject",
        "research_era",
        "purpose",
        "important_files",
        "conclusion_status",
        "superseding_commit",
        "paper_relevance",
        "audit_notes",
    }


def test_inventory_marks_human_review_fields_unreviewed() -> None:
    file_rows = _rows("paper-evidence/file-review.csv")
    commit_rows = _rows("paper-evidence/commit-review.csv")

    assert {row["classification"] for row in file_rows} == {"UNREVIEWED"}
    assert {row["conclusion_status"] for row in commit_rows} == {"UNREVIEWED"}
