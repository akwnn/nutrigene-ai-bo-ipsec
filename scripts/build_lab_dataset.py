#!/usr/bin/env python
"""Read every file under data/lab and write the derived tables.

    python scripts/build_lab_dataset.py                # full run, ~1 min
    python scripts/build_lab_dataset.py --no-verify    # skip SHA-256 re-hashing
    python scripts/build_lab_dataset.py --quick        # smaller images, for a smoke test

Nothing this writes is optimizer input. See boec.lab.dataset for the promotion rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from boec.lab.dataset import build_all  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lab-root", type=Path, default=REPO / "data" / "lab")
    ap.add_argument("--no-verify", action="store_true", help="skip SHA-256 re-hashing")
    ap.add_argument("--quick", action="store_true", help="analyse images at 512px long edge")
    args = ap.parse_args()

    if not args.lab_root.exists():
        print(f"lab root not found: {args.lab_root}", file=sys.stderr)
        return 1

    summary = build_all(
        args.lab_root,
        verify=not args.no_verify,
        long_edge=512 if args.quick else 1024,
    )
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nwrote {args.lab_root / 'derived'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
