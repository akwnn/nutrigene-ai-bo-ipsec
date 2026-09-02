from __future__ import annotations

import argparse
from pathlib import Path

from boec.paper_figures.export import build_all


def main() -> int:
    parser = argparse.ArgumentParser(description="Build publication-ready main figures from frozen artifacts.")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/paper-figures"))
    parser.add_argument("--preset", choices=("portable", "rsc", "nature", "plos", "presentation"), default="portable")
    args = parser.parse_args()
    manifest = build_all(args.results_dir, args.output_dir, args.preset)
    print(f"built {len(manifest['figures'])} figures for {args.preset} at {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
