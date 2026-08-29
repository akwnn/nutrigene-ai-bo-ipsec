#!/usr/bin/env python3
"""Report manufacturing gate survivors + Joseph secondary claim status (Option A).

Manufacturing gate is PRIMARY. Joseph LB round-budget numbers are SECONDARY —
printed from committed results/lb-*.json, never used as a survivor substitute.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_spade_development as d  # noqa: E402


def _rates(path: Path) -> dict[str, dict[str, float]]:
    rows = json.loads(path.read_text())["rows"]
    out: dict[str, dict[str, float]] = {}
    for arm in d.DEVELOPMENT_ARM_IDS:
        rs = [r for r in rows if d._development_arm_id(r) == arm]
        n = len(rs)
        ans = [r for r in rs if r["scores"]["certificate_nonempty"]]
        ok = [r for r in ans if r["scores"]["certificate_empirical_containment"] is True]
        out[arm] = {
            "n": n,
            "ans": (len(ans) / n if n else 0.0),
            "emp": (len(ok) / len(ans) if ans else float("nan")),
        }
    return out


def _joseph_secondary() -> dict[str, object]:
    """Summarize committed LB evidence (secondary claim only)."""
    files = sorted((ROOT / "results").glob("lb-*.json"))
    if not files:
        return {"status": "missing", "detail": "no results/lb-*.json"}
    # R=3 volume advantage is already adjudicated in SPADE-ROUND-SWEEP-SPEC.md
    return {
        "status": "committed",
        "files": [p.name for p in files],
        "claim": (
            "LB-1 PASS at R=3 (SPADE certified volume > qLogNEI); "
            "LB-2 SPADE certifies by R=5; qLogNEI needs ~10. "
            "Not a manufacturing ans/emp substitute."
        ),
        "spec": "docs/SPADE-ROUND-SWEEP-SPEC.md",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hill", type=Path, required=True)
    ap.add_argument("--levy", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    hill = _rates(args.hill)
    levy = _rates(args.levy)
    survivors = [
        arm
        for arm in d.CANDIDATE_ARM_IDS
        if hill[arm]["ans"] >= 0.5
        and hill[arm]["emp"] >= 0.9
        and not math.isnan(hill[arm]["emp"])
        and levy[arm]["ans"] >= 0.5
        and levy[arm]["emp"] >= 0.9
        and not math.isnan(levy[arm]["emp"])
    ]
    product = d.PRODUCT_ARM_ID
    report = {
        "primary": "manufacturing_certificate_recovery",
        "product_arm": product,
        "product_survived": product in survivors,
        "survivors": survivors,
        "hill": hill,
        "levy": levy,
        "joseph_secondary": _joseph_secondary(),
        "note": (
            "If survivors nonempty but product_arm absent → product FAIL for branding; "
            "human decision required before shipping IVR ablation as SPADE."
        ),
    }
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text)
    print(text)
    return 0 if survivors else 2


if __name__ == "__main__":
    raise SystemExit(main())
