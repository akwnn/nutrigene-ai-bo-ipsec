"""Version C section 3.2 -- detector statistics on the THREE FITTING FAMILIES.

    .venv/bin/python scripts/run_versionc_detector.py --seeds 10
    .venv/bin/python scripts/run_versionc_detector.py --smoke

Section 3.3's protocol is **freeze then score once**:

    1. Fit the rule and its threshold on hill, levy, rosenbrock ONLY.
    2. Freeze rule + threshold in docs/OPEN-QUESTIONS.md. Commit.
    3. Score ONCE on hartmann6 and ackley.

**Scoring the held-out families more than once is tuning on the evaluation set — the exact
failure this project exists to document.** So this runner **cannot reach them**:
:func:`evaluator_for` raises :class:`HeldOutFamily` by name for `hartmann6` and `ackley`,
and there is no flag that turns that off. A fitting run that can reach the evaluation
families is one `--family` away from invalidating the whole protocol, and the cheapest
place to make that impossible is here rather than in a reviewer's attention.

WHAT A ROW IS
-------------
One plate 1 -- a space-filling design of `n_plate1` wells, evaluated once, one GP fit --
and every section 3.2 statistic computed from it. **No oracle-derived column is carried**,
not even the optimum value: a threshold fitted on a column that does not exist at run time
on a real plate is not a detector, and a test asserts no such column leaks in.

WHAT THIS RUNNER DOES NOT DO
----------------------------
It does not fit the rule and it does not choose a threshold. It produces the table those
decisions will be made from. The rule is a **registration**, written into
`docs/OPEN-QUESTIONS.md` and committed **before** step 3 runs -- deliberately not in code,
which could be edited after the held-out scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.optimizers import lhs_design                               # noqa: E402
from boec.oracles import Levy, Rosenbrock, UnitScaled, load_ensemble  # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle, TorchEvaluator         # noqa: E402
from boec.versionc import (additive_refit_residual_ratio,            # noqa: E402
                           detector_statistics)

#: The FIT set, and the only families this runner can construct. Section 3.3.
FITTING_FAMILIES = ("hill", "levy", "rosenbrock")
#: Named so the refusal is legible. Never a parameter.
HELD_OUT_FAMILIES = ("hartmann6", "ackley")

N_PLATE1 = 40          # Version B's plate 1, unchanged
GRID_N, GRID_SEED = 20_000, 0
N_BINS = 20
CELLS = ((6, 0.25), (6, 0.10))
OUT = ROOT / "results" / "versionc-detector-fit.json"


class HeldOutFamily(RuntimeError):
    """A family outside the fitting set was requested.

    Raised **by name** rather than as a `KeyError`, so the traceback says why instead of
    looking like a typo. This is the single most consequential mistake available in this
    file: touching hartmann6 or ackley before the freeze silently converts the whole
    protocol into tuning on the evaluation set.
    """


def _instance_seed(family: str, dim: int, sigma: float, seed: int) -> int:
    """Deterministic and distinct per cell, derived by hash rather than by arithmetic on
    the seed, so a design here is never silently one some other experiment already drew."""
    key = f"versionc-detector|{family}|{dim}|{sigma}|{seed}".encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % (2 ** 31 - 1)


def evaluator_for(family: str, dim: int, sigma: float, seed: int):
    """``(evaluator, bounds, mu_max)`` for a **fitting** family. Raises otherwise."""
    if family in HELD_OUT_FAMILIES:
        raise HeldOutFamily(
            f"{family!r} is HELD OUT. Section 3.3 scores it exactly once, after the rule "
            f"and threshold are frozen in docs/OPEN-QUESTIONS.md and committed. The "
            f"fitting set is {FITTING_FAMILIES}.")
    if family not in FITTING_FAMILIES:
        raise HeldOutFamily(
            f"unknown family {family!r}; the fitting set is {FITTING_FAMILIES}")

    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    if family == "hill":
        # From the COMMITTED versioned ensemble, not sampled fresh. These are the same
        # landscapes every committed result was measured on, so a threshold fitted here
        # is fitted on the population the rest of the study reports.
        ensemble = load_ensemble(dim)
        inst = ensemble[seed % len(ensemble)]
        ev = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        return ev, bounds, float(inst.optimum_value)
    inner = Levy(dim=dim) if family == "levy" else Rosenbrock(dim=dim)
    oracle = UnitScaled(inner)
    ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
    return ev, bounds, float(oracle.optimum_value)


def plate_one(evaluator, bounds: torch.Tensor, n: int = N_PLATE1, seed: int = 0):
    """Version B's plate 1: a space-filling design, evaluated once. ``(X, Y, Yvar)``."""
    X = lhs_design(bounds, n, seed=seed)
    Y, Yvar = evaluator.evaluate(X)
    return X, Y, Yvar


def score_one(family: str, dim: int, sigma: float, seed: int, n_plate1: int = N_PLATE1,
              grid_n: int = GRID_N, n_bins: int = N_BINS) -> dict:
    """One plate 1, one GP, every section 3.2 statistic. **No oracle-derived column.**"""
    t0 = time.time()
    ev, bounds, _mu_max = evaluator_for(family, dim, sigma, seed)
    X, Y, Yvar = plate_one(ev, bounds, n=n_plate1, seed=seed)
    model = build_gp(X, Y, Yvar, bounds)

    stats = detector_statistics(model, X, bounds, grid_n=grid_n, grid_seed=GRID_SEED,
                                n_bins=n_bins)
    stats.update({
        "family": family, "dim": dim, "sigma": sigma, "seed": seed,
        "n_plate1": n_plate1,
        "additive_refit_residual": additive_refit_residual_ratio(X, Y, Yvar, bounds),
        "secs": round(time.time() - t0, 2),
    })
    # `mu_max` is deliberately NOT carried. It is oracle knowledge, and a threshold fitted
    # on a column a real plate cannot produce is not a detector.
    return stats


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch, gpytorch, numpy, scipy                           # noqa: E401
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=25)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    final = Path(args.out) if args.out else OUT
    cells = ((6, 0.10),) if args.smoke else CELLS
    seeds = range(2 if args.smoke else args.seeds)
    n_plate1 = 16 if args.smoke else N_PLATE1
    grid_n = 1024 if args.smoke else GRID_N

    total = len(FITTING_FAMILIES) * len(cells) * len(seeds)
    print(f"Version C section 3.2 · FITTING SET {FITTING_FAMILIES} · "
          f"held out {HELD_OUT_FAMILIES}")
    print(f"{total} rows · plate1={n_plate1} · grid={grid_n}\n")

    rows, n = [], 0
    partial = final.with_suffix(final.suffix + ".partial")
    for family in FITTING_FAMILIES:
        for dim, sigma in cells:
            for seed in seeds:
                rows.append(score_one(family, dim, sigma, seed, n_plate1=n_plate1,
                                      grid_n=grid_n))
                n += 1
                r = rows[-1]
                print(f"[{n:4d}/{total}] {family:<11} d={dim} s={sigma} seed={seed} "
                      f"comp={r['n_components_plausible']:<3d} "
                      f"peaks={r['n_peaks_raw']:<4d} "
                      f"conf={r['n_local_maxima']:<3d} "
                      f"add={r['additive_share']:.3f} "
                      f"ard={r['ard_separation_ratio']:.2f} "
                      f"resid={r['additive_refit_residual']:.2f} "
                      f"({r['secs']}s)", flush=True)
                partial.write_text(json.dumps(
                    {"status": "complete" if n == total else "partial",
                     "complete": n == total, "keys_present": n, "keys_expected": total,
                     "provenance": _provenance(sys.argv),
                     "config": {"fitting_families": list(FITTING_FAMILIES),
                                "held_out": list(HELD_OUT_FAMILIES),
                                "cells": [list(c) for c in cells],
                                "n_plate1": n_plate1, "grid_n": grid_n,
                                "grid_seed": GRID_SEED, "n_bins": N_BINS},
                     "rows": rows}, indent=1))
    final.write_text(partial.read_text())
    partial.unlink()
    print(f"\nwrote {final.name} · {len(rows)} rows")


if __name__ == "__main__":
    main()
