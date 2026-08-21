"""P5 · `tau_q` — tau as a per-family prevalence quantile. The table, and nothing else.

    .venv/bin/python scripts/run_p5_tau_quantile.py     # writes results/p5-tau-quantile.json

REGISTERED IN `docs/OPEN-QUESTIONS.md` (PHASES 2-4 PRE-REGISTRATION, P5) BEFORE THIS FILE
EXISTED. For a family `F` and dimension `d`, with `G` the registered 20,000-point Sobol
grid at seed 0 and `f` the NOISELESS oracle:

    tau_q(F, d, p) = Quantile_{x in G}( f(x), 1 - p )

so `{x in G : f(x) >= tau_q}` covers a fraction `p` of the grid **by construction,
identically on every family**. Registered grid: `p in {0.75, 0.25, 0.10, 0.01}`.

WHY A NEW ESTIMAND AND NOT A FIXED ONE
--------------------------------------
`tau_frac` is a fraction of `tau_max = mu_max*(1 - z*sigma_rel)`, and `mu_max` is exactly
1.0 on every family (COVERAGE-MATRIX B1), so tau is the same ABSOLUTE number everywhere.
What differs is what it selects. Measured on this grid, prevalence of the true superlevel
set at `tau_frac = 0.60`: ackley 0.00000, hartmann6 0.00805, hill 0.73569, levy 0.85745,
rosenbrock 0.95550. A cross-family table at fixed `tau_frac` compares an empty set against
one covering 95.6% of the box; it is not a comparison.

`tau_frac` is **not modified and not deprecated**. Every committed file keeps its meaning,
nothing already published is re-scored, and `tau_q` rows live in new files under a `p` key.

CALIBRATED AGAINST THE OLD GRID, NOT A REPLACEMENT FOR IT
---------------------------------------------------------
The four registered `p` reproduce the prevalence the committed `tau_frac` grid already
achieved on hill at d=6 -- 0.73569 / 0.28944 / 0.06844 / 0.00294 at `tau_frac`
0.60/0.75/0.85/0.95 -- to within 0.0394 (worst pair: p=0.25 against 0.28944). So hill is
scorable on BOTH grids and the two can be compared rather than swapped. The `calibration`
block below carries that measurement at both dimensions; at d=8 the worst pair is larger
than the figure P5 quotes, and it is recorded here rather than smoothed.

WHY THE GATE IS RECOMPUTATION AND NOT REPLAY
--------------------------------------------
`tau_q` is a deterministic function of a committed grid and a noiseless oracle. No campaign
is run, no noise is drawn and no seed matters, so there is nothing to replay: the check is
that the achieved prevalence equals `p` to within one grid cell (5e-5).
`tests/test_p5_tau_quantile.py` is that check.

HILL IS PER-INSTANCE, AND THAT IS NOT A DETAIL
----------------------------------------------
The hill "family" is 25 committed landscapes per dimension, each a different `f`. One
`tau_q` for hill would be an average of 25 different thresholds selecting 25 different
prevalences, which is the exact defect this estimand exists to remove. So hill carries one
row per (instance, d, p) and `tau_q("hill", ...)` refuses to run without an instance. The
instance set is read from `results/e2-grid.json` -- the committed column -- not from
`load_ensemble`, which holds 40 landscapes at d=6 against the 25 that were run.

ACKLEY
------
Under `tau_q` ackley's superlevel set is non-empty by construction, so the `CANNOT RUN`
verdict on it dissolves: it was a property of the threshold, not of the family. Ackley is
IN as a **declared sensitivity, never a headline** -- the CCD evaluates the box centre,
which is ackley's exact optimum, and the DoE arm attains the optimum in 7 of 25 instances.
Its rows carry `sensitivity: true` so the flag travels with the number.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch                                                          # noqa: E402

from boec.designspace import tau_max                                  # noqa: E402
from boec.norms import sobol_grid                                     # noqa: E402
from boec.oracles import (Ackley, Embedded, Hartmann6, HillOracle,    # noqa: E402
                          Levy, Rosenbrock, UnitScaled, load_ensemble)

OUT = ROOT / "results" / "p5-tau-quantile.json"
E2 = ROOT / "results" / "e2-grid.json"

#: The registered grid. Identical to `run_k6_designspace.py:57-58`.
GRID_N = 20_000
GRID_SEED = 0
#: The registered prevalences. Not a parameter -- a different p is a different estimand.
P_GRID = (0.75, 0.25, 0.10, 0.01)
DIMS = (6, 8)
#: The committed `tau_frac` grid, carried here ONLY for the calibration block.
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
#: `tau_max`'s own grid, for the reference table. A `tau_q` above `tau_max(gamma, sigma)`
#: sits over the predictive ceiling, so the certified set is empty for a reason that has
#: nothing to do with the design. Downstream needs to be able to see that.
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
SIGMAS = (0.25, 0.10)

#: UnitScaled + the family, exactly as `scripts/run_q42_families.py:88-92` builds it.
#: Hartmann6 is defined at d=6 only; `Embedded` gives it a fixed active subspace plus
#: inert nuisance axes at d=8, which is the Hill oracle's own structure.
FAMILIES = {"hartmann6": lambda d: (Hartmann6() if d == 6
                                    else Embedded(Hartmann6(), dim=d, seed=0)),
            "ackley": lambda d: Ackley(dim=d),
            "levy": lambda d: Levy(dim=d),
            "rosenbrock": lambda d: Rosenbrock(dim=d)}
ALL_FAMILIES = ("hill",) + tuple(FAMILIES)

_GRID: dict[int, torch.Tensor] = {}
_TRUTH: dict[tuple[str, int, str | None], np.ndarray] = {}


def grid(dim: int) -> torch.Tensor:
    """The registered ``(20000, dim)`` Sobol grid at seed 0."""
    if dim not in _GRID:
        _GRID[dim] = sobol_grid(dim, GRID_N, seed=GRID_SEED)
    return _GRID[dim]


def committed_hill_instances(dim: int) -> list[str]:
    """The 25 landscapes E2 actually ran at this dimension, from the committed grid."""
    rows = json.loads(E2.read_text())
    return sorted({r["instance"] for r in rows if r["dim"] == dim})


def grid_truth(family: str, dim: int, instance: str | None = None) -> np.ndarray:
    """``(20000,)`` the NOISELESS response on the registered grid. Cached per key."""
    if family not in ALL_FAMILIES:
        raise KeyError(f"unknown family {family!r}; expected one of {ALL_FAMILIES}")
    if family == "hill" and instance is None:
        raise ValueError("hill is 25 landscapes per dimension; pass instance=")
    key = (family, dim, instance)
    if key not in _TRUTH:
        X = grid(dim).numpy()
        if family == "hill":
            inst = next((i for i in load_ensemble(dim) if i.instance_id == instance), None)
            if inst is None:
                raise KeyError(f"instance {instance!r} not in the d={dim} ensemble")
            v = HillOracle(inst).f(X)
        else:
            v = UnitScaled(FAMILIES[family](dim)).f(X)
        _TRUTH[key] = np.asarray(v, dtype=float).reshape(-1)
    return _TRUTH[key]


def tau_q(family: str, dim: int, p: float, instance: str | None = None) -> float:
    """The registered estimand: the ``1 - p`` quantile of the noiseless `f` on the grid.

    `numpy`'s default linear interpolation is the reading of "Quantile" used here, and it
    is what makes the prevalence land on `p` exactly: at n = 20,000 none of the four
    registered `p` puts the interpolation point on a grid value, so the returned tau lies
    strictly between two grid values and `{f >= tau}` has exactly `round(p*n)` members.
    """
    return float(np.quantile(grid_truth(family, dim, instance), 1.0 - p))


def prevalence(family: str, dim: int, tau: float, instance: str | None = None) -> float:
    """Fraction of the grid in the TRUE superlevel set at this tau."""
    return float((grid_truth(family, dim, instance) >= tau).mean())


def _rows() -> list[dict]:
    out = []
    for dim in DIMS:
        for family in ALL_FAMILIES:
            insts = committed_hill_instances(dim) if family == "hill" else [None]
            for instance in insts:
                v = grid_truth(family, dim, instance)
                for p in P_GRID:
                    tau = tau_q(family, dim, p, instance)
                    out.append({
                        "family": family, "dim": dim, "instance": instance, "p": p,
                        "tau_q": tau,
                        "achieved_prevalence": prevalence(family, dim, tau, instance),
                        "n_selected": int((v >= tau).sum()),
                        "grid_min": float(v.min()), "grid_max": float(v.max()),
                        # DECISION 3: ackley is IN, but never as a headline.
                        "sensitivity": family == "ackley",
                    })
    return out


def _calibration() -> dict:
    """The `tau_frac` prevalences on hill that the four registered `p` are calibrated to.

    Measured here, not copied. `tau_max = 1.0` at gamma = 0.50, so `tau_frac` is the
    absolute threshold and this is the COVERAGE-MATRIX §2.4 hill row.
    """
    out = {}
    for dim in DIMS:
        insts = committed_hill_instances(dim)
        prev = [float(np.mean([prevalence("hill", dim, tf, i) for i in insts]))
                for tf in TAU_FRACS]
        out[f"d{dim}"] = {
            "n_instances": len(insts),
            "tau_fracs": list(TAU_FRACS),
            "hill_tau_frac_prevalence": prev,
            "p_grid": list(P_GRID),
            "abs_difference": [abs(p - q) for p, q in zip(P_GRID, prev)],
            "worst_abs_difference": max(abs(p - q) for p, q in zip(P_GRID, prev)),
        }
    return out


def _provenance(t0: float) -> dict:
    import botorch, gpytorch, scipy                                   # noqa: E401
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                         text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip())
    return {
        "git_sha": sha, "git_dirty": dirty,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "argv": sys.argv, "elapsed_s": round(time.time() - t0, 2),
        "python": platform.python_version(), "torch": torch.__version__,
        "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
        "numpy": np.__version__, "scipy": scipy.__version__,
    }


def main() -> None:
    t0 = time.time()
    if OUT.exists():
        # A committed result JSON is never overwritten. Delete it deliberately, or
        # write elsewhere -- but do not let a re-run silently replace the gate target.
        sys.exit(f"{OUT} exists; a committed result is never overwritten.")

    rows = _rows()
    doc = {
        "provenance": _provenance(t0),
        "config": {
            "estimand": "tau_q(F, d, p) = Quantile_{x in G}(f(x), 1 - p), G = the "
                        f"registered {GRID_N}-point Sobol grid at seed {GRID_SEED}, "
                        "f noiseless",
            "grid_n": GRID_N, "grid_seed": GRID_SEED, "p_grid": list(P_GRID),
            "dims": list(DIMS), "families": list(ALL_FAMILIES),
            "quantile_method": "numpy linear interpolation",
            "hill_instances_from": "results/e2-grid.json",
            "one_grid_cell": 1.0 / GRID_N,
            # Family-independent (COVERAGE-MATRIX B2: the noise model is bit-for-bit the
            # same on all five), so one table serves every family.
            "tau_max": {f"gamma={g}|sigma={s}": tau_max(g, s)
                        for s in SIGMAS for g in GAMMAS},
        },
        "calibration": _calibration(),
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, indent=1))

    worst = max(abs(r["achieved_prevalence"] - r["p"]) for r in rows)
    print(f"P5 · tau_q · {len(rows)} rows · worst |achieved - p| = {worst:.3e} "
          f"(one grid cell = {1/GRID_N:.1e})")
    hdr = "  ".join(f"p={p:<6}" for p in P_GRID)
    for dim in DIMS:
        print(f"\n  d={dim}   {'family':<12}{hdr}")
        for family in ALL_FAMILIES:
            sub = [r for r in rows if r["family"] == family and r["dim"] == dim]
            taus = [float(np.mean([r["tau_q"] for r in sub if r["p"] == p]))
                    for p in P_GRID]
            note = "  (sensitivity)" if family == "ackley" else ""
            note += "  (mean of 25)" if family == "hill" else ""
            print(f"         {family:<12}" + "  ".join(f"{t:<8.5f}" for t in taus) + note)
    for dim in DIMS:
        c = doc["calibration"][f"d{dim}"]
        print(f"\n  calibration d={dim}: hill tau_frac prevalence "
              + " ".join(f"{v:.5f}" for v in c["hill_tau_frac_prevalence"])
              + f"  worst |p - prevalence| = {c['worst_abs_difference']:.5f}")
    print(f"\n  -> {OUT.relative_to(ROOT)}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
