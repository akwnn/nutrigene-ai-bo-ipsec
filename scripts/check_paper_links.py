#!/usr/bin/env python3
"""Validate the publication reading path after repository consolidation."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
STALE_DOC = re.compile(r"docs/SPADE-(?:DOE-CERTIFICATE|ROUND-MATCHED|LC-CONFIRMATORY|TAU-DEGENERACY|THETA-TAU|PAPER-ARGUMENT|CONCLUSIONS|REAL-IPSC|PUBLISHED-ECM)")
REQUIRED = {
    "README.md", "LICENSE", "CITATION.cff", "paper/MANUSCRIPT.md", "paper/METHODS.md",
    "paper/SUPPLEMENT.md", "paper/PROTOCOLS.md", "paper/CLAIMS-AND-SOURCES.md",
    "paper-evidence/reproduction-map.md", "paper-evidence/file-review.csv",
    "paper-evidence/commit-review.csv", "archive/README.md",
}


def active_markdown() -> list[Path]:
    paths = [ROOT / "README.md"]
    paths += sorted((ROOT / "paper").glob("*.md"))
    paths += sorted((ROOT / "paper-evidence").rglob("*.md"))
    paths += sorted((ROOT / "archive").glob("README.md"))
    paths += sorted((ROOT / "archive").glob("*/README.md"))
    return paths


def validate() -> list[str]:
    errors: list[str] = []
    for relative in sorted(REQUIRED):
        if not (ROOT / relative).is_file():
            errors.append(f"missing required publication file: {relative}")

    for path in active_markdown():
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            clean = target.split("#", 1)[0].strip().strip("<>")
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / clean).resolve().exists():
                errors.append(f"broken link in {path.relative_to(ROOT)}: {target}")
        match = STALE_DOC.search(text)
        if match:
            errors.append(f"active prose references superseded document in {path.relative_to(ROOT)}: {match.group()}")
        for number_match in re.finditer(r"\+?0\.001353", text):
            line = text[: number_match.start()].count("\n") + 1
            context = " ".join(text.splitlines()[max(0, line - 2): line + 1]).lower()
            if not any(word in context for word in ("stale", "correct", "unsupported", "reject", "historical")):
                errors.append(f"stale C3 value lacks correction context: {path.relative_to(ROOT)}:{line}")

    expected = {
        *(f"dc-{family}.json" for family in ("ackley", "hartmann6", "hill", "levy", "rosenbrock")),
        *(f"lc-{family}.json" for family in ("ackley", "hartmann6", "hill", "levy", "rosenbrock")),
        *(f"tau-{family}.json" for family in ("ackley", "hartmann6", "hill", "levy", "rosenbrock")),
        *(f"tt-{family}.json" for family in ("ackley", "hartmann6", "hill", "levy", "rosenbrock")),
        *(f"la-{family}.json" for family in ("ackley", "hartmann6", "levy", "rosenbrock")),
        "replay-hall-ogle.log",
    }
    actual = {
        path.name for path in (ROOT / "results").iterdir()
        if path.is_file()
    }
    if actual != expected:
        errors.append(f"active result root mismatch; missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    return errors


def main() -> None:
    errors = validate()
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"publication path valid: {len(active_markdown())} Markdown files, {len(REQUIRED)} required artifacts")


if __name__ == "__main__":
    main()
