"""K2 -- the design lottery, gates Piece B (OA-LHS Plate 1).

Registered: docs/SPADE-CALIBRATION-FIX-SPEC.md sec 4. Matches
results/q53-spread-gp-hartmann6.json's exact sampling structure (25 seeds x 5 draws each,
d=6, sigma=0.25, hartmann6) so the two design-SD distributions are directly comparable.
Monkeypatches `boec.spread_gp.lhs_design` -> `oa_lhs_design` for the duration of each call
(module-level attribute swap, restored after) rather than editing spread_gp.py, which is
frozen; `spread_gp_once` itself is otherwise called completely unmodified, so the GP fit,
locator settings and (rule_a, rule_c) computation are bit-for-bit what produced the
committed comparator.

    .venv/bin/python -u scripts/analyse_k2_design_lottery.py --pilot
    .venv/bin/python -u scripts/analyse_k2_design_lottery.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import boec.spread_gp as spread_gp                                    # noqa: E402
from boec.oracles import Hartmann6, UnitScaled                        # noqa: E402
from boec.optimizers import oa_lhs_design                             # noqa: E402
from boec.spread_gp import design_average, spread_gp_once             # noqa: E402
from boec.torch_oracle import TorchEvaluator                          # noqa: E402

DIM, SIGMA, N_OA = 6, 0.25, 49
N_REPS, N_DRAWS = 25, 5
COMMITTED = ROOT / "results" / "q53-spread-gp-hartmann6.json"
OUT = ROOT / "results" / "k2-design-lottery.json"


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double), torch.ones(d, dtype=torch.double)])


def _design_seed(seed: int, draw: int) -> int:
    key = f"k2|oa_lhs|hartmann6|{DIM}|{SIGMA}|{seed}|{draw}".encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % (2**31 - 1)


def _oa_lhs_at_n(bounds: torch.Tensor, n: int, *, seed: int = 0) -> torch.Tensor:
    """`spread_gp_once` calls its design generator with `n=BUDGET` (48 elsewhere); this
    project's spread arms are always scored at one fixed n. K2 tests OA-LHS at its own
    required n=49, so the swapped-in generator ignores whatever `n` spread_gp_once passes
    and always builds at N_OA -- the one-well mismatch this spec registers openly."""
    return oa_lhs_design(bounds, N_OA, seed=seed)


def committed_reference() -> list[float]:
    d = json.loads(COMMITTED.read_text())
    rows = d["rows"] if isinstance(d, dict) else d
    return [float(r["spread_a_sd"]) for r in rows
            if r.get("dim") == DIM and r.get("sigma") == SIGMA
            and not np.isnan(r["spread_a_sd"])]


def one_seed(oracle, bounds: torch.Tensor, opt: float, seed: int, n_draws: int) -> dict:
    a_draws, c_draws = [], []
    for draw in range(n_draws):
        ev = TorchEvaluator(oracle, sigma_rel=SIGMA, seed=seed)
        a, c = spread_gp_once(ev, bounds, truth=ev.truth, optimum_value=opt,
                              n=N_OA, seed=_design_seed(seed, draw))
        a_draws.append(a)
        c_draws.append(c)
    a_mean, a_sd = design_average(a_draws)
    c_mean, c_sd = design_average(c_draws)
    return {"seed": seed, "spread_a": a_mean, "spread_a_sd": a_sd,
            "spread_c": c_mean, "spread_c_sd": c_sd, "a_draws": a_draws, "c_draws": c_draws}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--reps", type=int, default=N_REPS)
    args = ap.parse_args()

    inner = Hartmann6()  # fixed at d=6, matching FAMILIES["hartmann6"] in run_q53
    oracle = UnitScaled(inner)
    bounds, opt = _bounds(DIM), float(oracle.optimum_value)

    original_lhs = spread_gp.lhs_design
    spread_gp.lhs_design = _oa_lhs_at_n
    try:
        if args.pilot:
            t0 = time.time()
            row = one_seed(oracle, bounds, opt, 0, 5)
            print(f"pilot: 1 seed x 5 draws in {time.time()-t0:.1f}s "
                  f"({(time.time()-t0)/5:.1f}s/campaign) -- spread_a_sd={row['spread_a_sd']:.4f}")
            est = (time.time() - t0) / 5 * N_REPS * N_DRAWS
            print(f"estimated full run ({N_REPS}x{N_DRAWS}={N_REPS*N_DRAWS} campaigns): "
                  f"{est/60:.0f} min")
            return

        rows, t0 = [], time.time()
        for seed in range(args.reps):
            rows.append(one_seed(oracle, bounds, opt, seed, N_DRAWS))
            print(f"[{seed+1:2d}/{args.reps}] spread_a_sd={rows[-1]['spread_a_sd']:.4f} "
                  f"({(time.time()-t0)/60:.1f}m)", flush=True)
    finally:
        spread_gp.lhs_design = original_lhs

    oa_sds = np.array([r["spread_a_sd"] for r in rows])
    ref_sds = np.array(committed_reference())

    rng = np.random.default_rng(0)
    boot = np.array([oa_sds[rng.integers(0, len(oa_sds), len(oa_sds))].mean()
                     - ref_sds[rng.integers(0, len(ref_sds), len(ref_sds))].mean()
                     for _ in range(4000)])
    ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
    diff = float(oa_sds.mean() - ref_sds.mean())

    verdict = ("WIN -- OA-LHS design SD materially below plain-LHS's" if ci_hi < 0 else
               "KILL -- design SD not materially reduced" if ci_lo <= 0 <= ci_hi else
               "UNEXPECTED -- OA-LHS design SD is HIGHER than plain-LHS's")

    out = {"n_reps": len(rows), "n_draws_per_rep": N_DRAWS, "n_oa": N_OA,
           "oa_lhs_design_sd_mean": float(oa_sds.mean()),
           "oa_lhs_design_sd_range": [float(oa_sds.min()), float(oa_sds.max())],
           "plain_lhs_design_sd_mean_ref": float(ref_sds.mean()),
           "plain_lhs_design_sd_range_ref": [float(ref_sds.min()), float(ref_sds.max())],
           "diff_oa_minus_plain": diff, "bootstrap_ci_95": [float(ci_lo), float(ci_hi)],
           "verdict": verdict, "rows": rows,
           "spec": "docs/SPADE-CALIBRATION-FIX-SPEC.md sec 4"}
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nOA-LHS design SD: {oa_sds.mean():.4f} {[round(x,4) for x in [oa_sds.min(),oa_sds.max()]]}")
    print(f"plain-LHS design SD (ref, Q53): {ref_sds.mean():.4f} "
          f"{[round(x,4) for x in [ref_sds.min(),ref_sds.max()]]}")
    print(f"diff (OA - plain): {diff:+.4f}, 95% CI [{ci_lo:+.4f}, {ci_hi:+.4f}]")
    print(verdict)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
