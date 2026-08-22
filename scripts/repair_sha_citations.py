"""Repair commit-SHA citations in the docs after the `p6-families.json` history purge.

**Why this is needed.** Purging a blob from history changes every commit SHA from the purge
point onward. The docs cite roughly fifty of them, and at least one citation is load-bearing
rather than decorative: the detector freeze is evidence *because* it is a commit that
precedes the scoring pass (`FINDINGS §37`, `OPEN-QUESTIONS` C3.3). **The rewrite preserves
that ordering but breaks the name of the thing being ordered**, so citations must be
remapped rather than dropped.

**How the map is built.** The rewrite preserves commit order and count, so the *i*-th commit
of ``git rev-list --reverse <range>`` before corresponds to the *i*-th after. The
before-list is captured to a file prior to the rewrite; this script recomputes the
after-list and zips them positionally.

**Safety.** Dry run by default; ``--apply`` writes. Refuses outright if the two lists differ
in length, because that means a commit was dropped or added and positional correspondence is
void — in which case the map must be rebuilt from the rewrite tool's own commit map instead.

Usage::

    .venv/bin/python scripts/repair_sha_citations.py --before <file>          # dry run
    .venv/bin/python scripts/repair_sha_citations.py --before <file> --apply
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

#: Shortened forms that appear in prose. Longest first at substitution time so a full
#: 40-character sha is never clipped by a match on its own 7-character prefix.
WIDTHS = (40, 12, 10, 9, 8, 7)


def _rev_list(rng: str) -> list[str]:
    out = subprocess.check_output(["git", "rev-list", "--reverse", rng],
                                  cwd=ROOT, text=True)
    return out.split()


def build_map(before_file: Path, rng: str) -> dict[str, str]:
    """``{old_prefix: new_prefix}`` for every width in :data:`WIDTHS`."""
    before = [tok.strip() for tok in before_file.read_text().split() if tok.strip()]
    after = _rev_list(rng)
    if len(before) != len(after):
        raise SystemExit(
            f"REFUSING: {len(before)} commits before the rewrite, {len(after)} after. "
            f"A commit was dropped or added, so positional mapping is invalid. Rebuild "
            f"the map from the rewrite tool's own commit map instead of guessing.")
    mapping: dict[str, str] = {}
    for old, new in zip(before, after):
        if old == new:
            continue
        for n in WIDTHS:
            mapping[old[:n]] = new[:n]
    return mapping


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True,
                    help="ordered SHA list captured BEFORE the rewrite")
    ap.add_argument("--range", default="b66bd45..HEAD",
                    help="the same range the purge was run over")
    ap.add_argument("--apply", action="store_true",
                    help="write the changes; default is a dry run")
    args = ap.parse_args()

    mapping = build_map(Path(args.before), args.range)
    n_commits = len({v for v in mapping.values() if len(v) == 40})
    print(f"{n_commits} commits changed SHA\n")
    if not mapping:
        print("nothing to remap -- either the rewrite has not run yet, or no SHA moved")
        return

    total = 0
    for doc in sorted(DOCS.glob("*.md")):
        text = doc.read_text()
        hits = 0
        for old in sorted(mapping, key=len, reverse=True):
            text, n = re.subn(rf"\b{re.escape(old)}\b", mapping[old], text)
            hits += n
        if hits:
            print(f"  {doc.name:<26} {hits:>4} citations")
            total += hits
            if args.apply:
                doc.write_text(text)
    verb = "REWRITTEN" if args.apply else "would be rewritten (dry run)"
    print(f"\n{total} citations {verb}")
    if not args.apply:
        print("re-run with --apply to write them")


if __name__ == "__main__":
    main()
