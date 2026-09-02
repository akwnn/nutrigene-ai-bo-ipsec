"""K0 -- does sup-norm error or R^2 govern regret? Gates Piece A (docs/ODIN-VERDICT.md sec 6).

Registered: docs/SPADE-CALIBRATION-FIX-SPEC.md sec 1. No new campaigns -- reads
results/p2-versionb-gamma.json, dedupes 4,800 rows (24 scoring cells per campaign) down
to 200 unique campaigns, and correlates sup_err/grid_r2 against regret.

    .venv/bin/python scripts/analyse_k0_calibration_gate.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "p2-versionb-gamma.json"
OUT = ROOT / "results" / "k0-calibration-gate.json"


def main() -> None:
    d = json.loads(SRC.read_text())
    rows = d["rows"] if isinstance(d, dict) else d

    seen, campaigns = set(), []
    for r in rows:
        key = (r["arm"], r["seed"], r["instance"])
        if key in seen:
            continue
        seen.add(key)
        campaigns.append(r)
    assert len(campaigns) == 200, f"expected 200 unique campaigns, got {len(campaigns)}"

    sup_err = np.array([float(c["sup_err"]) for c in campaigns])
    grid_r2 = np.array([float(c["grid_r2"]) for c in campaigns])
    regret = np.array([float(c["regret"]) for c in campaigns])

    rho_sup, p_sup = spearmanr(sup_err, regret)
    rho_r2, p_r2 = spearmanr(grid_r2, regret)

    rng = np.random.default_rng(0)
    n = len(campaigns)
    diffs = np.empty(4000)
    for b in range(4000):
        idx = rng.integers(0, n, n)
        rs, _ = spearmanr(sup_err[idx], regret[idx])
        rr, _ = spearmanr(grid_r2[idx], regret[idx])
        diffs[b] = abs(rr) - abs(rs)
    ci_lo, ci_hi = np.percentile(diffs, [2.5, 97.5])

    verdict = ("KILL -- R2 correlates at least as strongly as sup_err; Stage 2 stays "
               "deleted" if abs(rho_r2) >= abs(rho_sup) else
               "REVIVE -- sup_err correlates and R2 does not; Piece A goes back on the "
               "table, gated by K1")

    out = {
        "n_campaigns": n,
        "rho_sup_err_regret": float(rho_sup), "p_sup_err_regret": float(p_sup),
        "rho_grid_r2_regret": float(rho_r2), "p_grid_r2_regret": float(p_r2),
        "abs_diff_r2_minus_sup": float(abs(rho_r2) - abs(rho_sup)),
        "bootstrap_ci_95": [float(ci_lo), float(ci_hi)],
        "verdict": verdict,
        "source": str(SRC.relative_to(ROOT)),
        "spec": "docs/SPADE-CALIBRATION-FIX-SPEC.md sec 1",
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
