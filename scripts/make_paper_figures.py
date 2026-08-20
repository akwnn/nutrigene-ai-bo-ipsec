"""Write the three paper figures to docs/figures/.

    python scripts/make_paper_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.paper_figures import make_paper_figures, winner_reverses  # noqa: E402


def main() -> None:
    paths = make_paper_figures()
    print(f"  rank reversal in {winner_reverses()} of 4 settings")
    for name, pair in paths.items():
        for kind, path in pair.items():
            rel = path.relative_to(ROOT)
            print(f"  {name} {kind}: {rel}  ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
