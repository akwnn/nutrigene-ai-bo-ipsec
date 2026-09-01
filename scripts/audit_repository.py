#!/usr/bin/env python3
"""Build and validate the human-reviewed SPADE repository audit ledgers."""

from __future__ import annotations

import argparse
import csv
import subprocess
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "6e4f22e"
EXPECTED_COMMITS = 719
FILE_REVIEW = ROOT / "paper-evidence" / "file-review.csv"
COMMIT_REVIEW = ROOT / "paper-evidence" / "commit-review.csv"

FILE_FIELDS = [
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
]
COMMIT_FIELDS = [
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
]
ALLOWED_CLASSIFICATIONS = {
    "CORE",
    "SUPPORT",
    "INFRASTRUCTURE",
    "ARCHIVE-VALID",
    "ARCHIVE-SUPERSEDED",
    "ARCHIVE-FAILED/VOID",
    "GENERATED/DISPOSABLE",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def read_rows(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def write_rows(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def baseline_paths() -> list[str]:
    return git("ls-tree", "-r", "--name-only", BASELINE).splitlines()


def baseline_commits() -> list[str]:
    return git("rev-list", BASELINE).splitlines()


def path_history() -> dict[str, list[str]]:
    """Return commits touching each path at its baseline name.

    A single history traversal keeps inventory generation fast. Human review records
    earlier renamed paths where that distinction matters scientifically.
    """

    output = git("log", BASELINE, "--format=@@COMMIT@@%H", "--name-only")
    history: dict[str, list[str]] = {}
    commit = ""
    for line in output.splitlines():
        if line.startswith("@@COMMIT@@"):
            commit = line.removeprefix("@@COMMIT@@")
        elif line and commit:
            history.setdefault(line, []).append(commit)
    return history


def file_type(path: str) -> str:
    name = Path(path).name
    if "." not in name:
        return "[none]"
    return Path(path).suffix.lower().removeprefix(".") or "[none]"


def inventory_files() -> None:
    existing = read_rows(FILE_REVIEW, "baseline_path")
    history = path_history()
    rows: list[dict[str, str]] = []
    for path in sorted(baseline_paths()):
        prior = existing.get(path, {})
        commits = history.get(path, [])
        row = {field: prior.get(field, "UNREVIEWED") for field in FILE_FIELDS}
        row.update(
            {
                "baseline_path": path,
                "file_type": file_type(path),
                "first_commit": commits[-1] if commits else "UNRESOLVED",
                "latest_meaningful_commit": prior.get(
                    "latest_meaningful_commit", commits[0] if commits else "UNRESOLVED"
                ),
            }
        )
        rows.append(row)
    write_rows(FILE_REVIEW, FILE_FIELDS, rows)


def inventory_commits() -> None:
    existing = read_rows(COMMIT_REVIEW, "commit")
    record_format = "%H%x1f%ad%x1f%s%x1e"
    output = git("log", BASELINE, f"--format={record_format}", "--date=short")
    rows: list[dict[str, str]] = []
    for record in output.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        commit, date, subject = record.split("\x1f", maxsplit=2)
        prior = existing.get(commit, {})
        row = {field: prior.get(field, "UNREVIEWED") for field in COMMIT_FIELDS}
        row.update({"commit": commit, "date": date, "subject": subject})
        rows.append(row)
    write_rows(COMMIT_REVIEW, COMMIT_FIELDS, rows)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise SystemExit(f"missing audit ledger: {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def require_unique(rows: list[dict[str, str]], key: str, expected: set[str]) -> None:
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise SystemExit(f"duplicate {key} values in audit ledger")
    if set(values) != expected:
        missing = sorted(expected - set(values))[:5]
        extra = sorted(set(values) - expected)[:5]
        raise SystemExit(f"{key} coverage mismatch; missing={missing}, extra={extra}")


def validate_inventory() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    file_fields, file_rows = load_csv(FILE_REVIEW)
    commit_fields, commit_rows = load_csv(COMMIT_REVIEW)
    if file_fields != FILE_FIELDS:
        raise SystemExit("file-review.csv header does not match the required schema")
    if commit_fields != COMMIT_FIELDS:
        raise SystemExit("commit-review.csv header does not match the required schema")
    require_unique(file_rows, "baseline_path", set(baseline_paths()))
    commits = set(baseline_commits())
    if len(commits) != EXPECTED_COMMITS:
        raise SystemExit(
            f"baseline commit count changed: expected {EXPECTED_COMMITS}, got {len(commits)}"
        )
    require_unique(commit_rows, "commit", commits)
    return file_rows, commit_rows


def validate_commits() -> None:
    _, commit_rows = validate_inventory()
    review_fields = [
        "research_era",
        "purpose",
        "important_files",
        "conclusion_status",
        "superseding_commit",
        "paper_relevance",
        "audit_notes",
    ]
    incomplete = [
        row["commit"]
        for row in commit_rows
        if any(not row[field] or row[field] == "UNREVIEWED" for field in review_fields)
    ]
    if incomplete:
        raise SystemExit(f"{len(incomplete)} commits remain unreviewed; first={incomplete[0]}")


def validate_complete() -> None:
    file_rows, _ = validate_inventory()
    validate_commits()
    review_fields = [
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
    ]
    incomplete = [
        row["baseline_path"]
        for row in file_rows
        if any(not row[field] or row[field] == "UNREVIEWED" for field in review_fields)
    ]
    if incomplete:
        raise SystemExit(f"{len(incomplete)} files remain unreviewed; first={incomplete[0]}")
    invalid = [
        row["baseline_path"]
        for row in file_rows
        if row["classification"] not in ALLOWED_CLASSIFICATIONS
    ]
    if invalid:
        raise SystemExit(f"invalid file classifications; first={invalid[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("inventory", "validate-inventory", "validate-commits", "validate"),
    )
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_files()
        inventory_commits()
        validate_inventory()
    elif args.command == "validate-inventory":
        validate_inventory()
    elif args.command == "validate-commits":
        validate_commits()
    else:
        validate_complete()


if __name__ == "__main__":
    main()
