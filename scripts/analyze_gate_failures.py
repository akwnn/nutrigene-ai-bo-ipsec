#!/usr/bin/env python3
"""Summarize hill+levy gate shards for abstention and empirical containment."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import run_spade_development as development  # noqa: E402


def _load_rows(path: Path) -> list[dict]:
    if path.suffix == ".gz":
        from boec.spade_study import read_jsonl_gzip

        return list(read_jsonl_gzip(path))
    payload = json.loads(path.read_text())
    if isinstance(payload, dict) and "rows" in payload:
        return payload["rows"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"unsupported shard format: {path}")


def _rates(rows: list[dict], arm: str) -> dict[str, float | int]:
    subset = [row for row in rows if development._development_arm_id(row) == arm]
    answered = [
        row
        for row in subset
        if row["scores"]["certificate_nonempty"]
    ]
    contained = [
        row
        for row in answered
        if row["scores"]["certificate_empirical_containment"] is True
    ]
    abstentions: dict[str, int] = defaultdict(int)
    for row in subset:
        reason = row["scores"].get("certificate_abstention_reason")
        if reason:
            abstentions[str(reason)] += 1
    n = len(subset)
    return {
        "n": n,
        "ans": (len(answered) / n if n else 0.0),
        "emp": (len(contained) / len(answered) if answered else float("nan")),
        "abstentions": dict(abstentions),
    }


def summarize(paths: list[Path], families: tuple[str, ...]) -> dict[str, object]:
    by_family: dict[str, dict[str, dict[str, object]]] = {}
    arms: set[str] = set()
    for path in paths:
        rows = _load_rows(path)
        family = rows[0]["family"] if rows else path.stem.split("-")[2]
        if family not in families:
            continue
        by_family.setdefault(family, {})
        for row in rows:
            arms.add(development._development_arm_id(row))
    for family in families:
        rows: list[dict] = []
        for path in paths:
            loaded = _load_rows(path)
            if loaded and loaded[0]["family"] == family:
                rows.extend(loaded)
        by_family[family] = {arm: _rates(rows, arm) for arm in sorted(arms)}
    survivors = [
        arm
        for arm in sorted(arms)
        if all(
            by_family.get(family, {}).get(arm, {}).get("ans", 0.0) >= 0.5
            and by_family.get(family, {}).get(arm, {}).get("emp", 0.0) >= 0.9
            for family in families
        )
    ]
    return {"families": by_family, "survivors": survivors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "shards",
        nargs="+",
        type=Path,
        help="resume JSON or jsonl.gz development shards",
    )
    parser.add_argument(
        "--families",
        nargs="+",
        default=["hill", "levy"],
        help="families that must jointly pass (default: hill levy)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="optional JSON output path",
    )
    args = parser.parse_args(argv)
    report = summarize(args.shards, tuple(args.families))
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0 if report["survivors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
