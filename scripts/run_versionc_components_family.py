"""Version C section 4's registered prediction, on the family that discriminates it.

    .venv/bin/python scripts/run_versionc_components_family.py --seeds 25

**The prediction, registered in `run_versionc_form1.COMPONENT_PREDICTION` before any
component number existed:** the effect should be **largest on hartmann6** (multimodal,
disconnected superlevel sets, so a single inscribed box is bounded by the largest
component) and **near-zero on hill** (unimodal, one component, so the decomposition has
nothing to recover). *"If it helps everywhere equally, something is wrong."*

FINDINGS §38.5 confirmed the **hill** half on committed data — 1.07 components at
γ=0.50 τ=0.60, box gain +0.0004 — and recorded the **hartmann6** half as NOT RUN. This
runner is that half, and it carries the hill control so the result is a contrast rather
than a single number.

WHY THIS IS SMALL WHERE `run_versionc_form1` IS LARGE
------------------------------------------------------
`run_versionc_form1` emits the full K6 row so its shared columns can be gated at
``|delta| = 0`` against the committed file; that costs ~48 MB per σ. **Nothing here needs
gating**, because no committed file carries a component count — the columns are new. So the
row is the component columns and nothing else, and the output is a few hundred kB.

THE SCREENED ARM IS EXCLUDED, BY NAME
--------------------------------------
FINDINGS §38.6: ``doe`` has ``n_active = 4`` and its box volume takes only ``{0.0, 1.0}``.
With the inactive axes pinned, almost no grid point falls inside a candidate box,
``mask[inside].all()`` is vacuously true, and the box fills the active subspace — so
summing per-component boxes multiplies 1.0 by the component count and produces a **+59**.
Including it would put that number in a table about multimodality.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
import platform
import statistics as st
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

from boec.designspace import (component_report, gp_adapter,            # noqa: E402
                              grid_neighbours, predictive_probability_map, tau_max)
from boec.norms import sobol_grid                                      # noqa: E402
from boec.replay import regenerate, unit_bounds                        # noqa: E402
from boec.surrogate import build_gp                                    # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_F1 = _load("_run_versionc_form1", ROOT / "scripts" / "run_versionc_form1.py")

#: Imported from the runner that registered it, never restated. A prediction retyped in
#: the file that tests it is a prediction that can drift.
PREDICTION = _F1.COMPONENT_PREDICTION

#: The target and its control. hartmann6 alone cannot show "largest".
FAMILIES = ("hill", "hartmann6")

EXCLUDED_ARMS = {
    "doe": ("n_active = 4 and box volume takes only {0.0, 1.0}; with inactive axes pinned "
            "the containment test is vacuously true and the box fills the active "
            "subspace, so summing per-component boxes multiplies 1.0 by the component "
            "count (FINDINGS 38.6)"),
}

ARMS = ("versionb", "lhs", "qlognei")
CELLS = ((6, 0.25), (6, 0.10))
GAMMAS = (0.50, 0.90)
TAU_FRACS = (0.60, 0.85)
GRID_N, GRID_SEED = 20_000, 0
OUT = ROOT / "results" / "versionc-components-family.json"

_VERSIONB_MODE = {"versionb": "lse", "versionb_random": "random",
                  "versionb_predictive": "predictive"}
_VB = _load("_run_versionb", ROOT / "scripts" / "run_versionb.py")


def _instance_for(family: str, dim: int, seed: int) -> str:
    """What ``regenerate`` wants as its first argument.

    Off Hill it is the **family label** -- family campaigns are keyed by
    ``(family, dim, sigma, seed)`` and carry no ``instance_id``. **On Hill it is a real
    ``instance_id``** from the committed ensemble, because Hill is a family of sampled
    landscapes rather than one function. Passing "hill" raises
    ``KeyError: instance 'hill' not in the d=6 ensemble`` -- which is what the first
    version of this file did, and what the test caught.
    """
    if family != "hill":
        return family
    from boec.oracles import load_ensemble
    ensemble = load_ensemble(dim)
    return ensemble[seed % len(ensemble)].instance_id


def _regenerate(family: str, dim: int, sigma: float, seed: int, arm: str):
    """One campaign, through ``replay.regenerate``'s own family path."""
    inst = _instance_for(family, dim, seed)
    if arm in _VERSIONB_MODE:
        mode = _VERSIONB_MODE[arm]

        def _builder(orc, d, sd, _m=mode):
            mu = float(getattr(orc, "optimum_value", 1.0))
            X, Y, V, _diag = _VB._two_plate(orc, d, sd, mu, _m)
            return X, Y, V, None, None

        return regenerate(inst, dim, sigma, seed, arm, family=family, builder=_builder)
    replay_arm = "lhs" if arm == "plate1_only" else arm
    return regenerate(inst, dim, sigma, seed, replay_arm, family=family)


def _oracle_for(family: str, dim: int, sigma: float, seed: int):
    """The same oracle the regeneration used, for the noiseless truth on the grid.

    Two paths, because Hill is not in ``FAMILY_ORACLE``: it is a family of **sampled
    landscapes** carrying an ``instance_id``, while the analytic families are one function
    each. ``run_p6_families.rec_oracle`` delegates straight to ``family_evaluator`` and so
    handles the analytic four only -- P6 never runs Hill. Calling it for Hill raises.

    ``truth`` draws no noise, so a fresh evaluator cannot disturb the campaign's stream --
    but it must be the SAME oracle, or the map is scored against a different landscape
    from the one that was searched.
    """
    if family == "hill":
        from boec.replay import instance_by_id
        from boec.torch_oracle import BiphasicOracle
        return BiphasicOracle(instance_by_id(_instance_for(family, dim, seed), dim),
                              sigma_rel=sigma, seed=seed)
    from boec.replay import family_evaluator
    return family_evaluator(family, dim, sigma, seed)


def score_one(family: str, dim: int, sigma: float, seed: int, arm: str,
              grid_n: int = GRID_N, gammas=GAMMAS, tau_fracs=TAU_FRACS,
              grid=None, neighbours=None) -> list[dict]:
    """Component columns only. No gated column, because none exists to gate against."""
    rec = _regenerate(family, dim, sigma, seed, arm)
    bounds = unit_bounds(dim)
    grid = sobol_grid(dim, grid_n, seed=GRID_SEED) if grid is None else grid

    orc = _oracle_for(family, dim, sigma, seed)
    model = build_gp(rec.X, rec.Y, rec.Yvar, bounds)
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)
    sigma_pred = ((sigma * mean).abs() ** 2 + float(orc.sigma_add) ** 2).sqrt()

    class _M:
        def posterior_mean_and_sd(self, Z):
            return mean, sd

    with torch.no_grad():
        truth = orc.truth(grid).reshape(-1).double()

    mu_max = float(rec.optimum_value)
    rows = []
    for gamma in gammas:
        tmax = tau_max(gamma, sigma, mu_max)
        for tf in tau_fracs:
            tau = round(tf * tmax, 10)
            p_pred = predictive_probability_map(_M(), grid, tau, sigma_pred)
            d_gamma = p_pred >= gamma
            comps = component_report(d_gamma, grid, truth, tau, neighbours=neighbours,
                                     seed_score=p_pred)
            rows.append({
                "family": family, "dim": dim, "sigma": sigma, "seed": seed, "arm": arm,
                "gamma": gamma, "tau_frac": tf, "tau": tau,
                "n_components": comps[0]["n_components"] if comps else 0,
                "vol_pred": float(d_gamma.double().mean()),
                "largest_component_vol": comps[0]["vol"] if comps else 0.0,
                "component_box_vol_sum": sum(c["box_vol"] for c in comps),
                "box_vol_all_components": (comps[0]["box_vol_all_components"]
                                           if comps else 0.0),
            })
    del model, mean, sd
    gc.collect()
    return rows


def verdict(rows: list[dict]) -> dict:
    """Does the registered prediction hold? Refuses on one family.

    A verdict computed from the target alone is not a contrast, and reporting hartmann6's
    number as though it were "the effect" would be exactly the error the control exists to
    prevent.
    """
    fams = {r["family"] for r in rows}
    missing = set(FAMILIES) - fams
    if missing:
        raise ValueError(
            f"the prediction is a CONTRAST and {sorted(missing)} is absent; a verdict from "
            f"{sorted(fams)} alone would report the target's number as the effect")

    out = {}
    for f in FAMILIES:
        sub = [r for r in rows if r["family"] == f]
        out[f] = {
            "n": len(sub),
            "mean_components": st.mean(r["n_components"] for r in sub),
            "mean_box_gain": st.mean(r["component_box_vol_sum"]
                                     - r["box_vol_all_components"] for r in sub),
        }
    tgt, ctl = out[PREDICTION["largest"]], out[PREDICTION["near_zero"]]
    holds = (tgt["mean_components"] > ctl["mean_components"]
             and tgt["mean_box_gain"] > ctl["mean_box_gain"])
    return {
        "prediction": PREDICTION, "per_family": out, "prediction_holds": bool(holds),
        "note": (
            f"{PREDICTION['largest']} exceeds {PREDICTION['near_zero']} on both component "
            f"count and box gain -- the decomposition recovers structure where the "
            f"superlevel set is disconnected and not where it is not"
            if holds else
            f"the prediction does NOT hold: the decomposition does not separate "
            f"{PREDICTION['largest']} from {PREDICTION['near_zero']}. Registered in "
            f"advance as the failure case -- 'if it helps everywhere equally, something "
            f"is wrong'"),
    }


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=25)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    final = Path(args.out) if args.out else OUT
    seeds = range(2 if args.smoke else args.seeds)
    grid_n = 2048 if args.smoke else GRID_N
    cells = ((6, 0.25),) if args.smoke else CELLS

    print(f"Version C section 4's registered prediction · {PREDICTION['largest']} vs "
          f"{PREDICTION['near_zero']}")
    print(f"  {PREDICTION['why']}\n")

    grid = sobol_grid(6, grid_n, seed=GRID_SEED)
    print("building the grid neighbour graph once ...", flush=True)
    neighbours = grid_neighbours(grid)

    rows, n = [], 0
    total = len(FAMILIES) * len(cells) * len(seeds) * len(ARMS)
    for family in FAMILIES:
        for dim, sigma in cells:
            for seed in seeds:
                for arm in ARMS:
                    t0 = time.time()
                    try:
                        got = score_one(family, dim, sigma, seed, arm, grid_n=grid_n,
                                        grid=grid, neighbours=neighbours)
                    except Exception as e:                          # noqa: BLE001
                        print(f"  ! {family} {arm} seed={seed}: {type(e).__name__}: {e}",
                              flush=True)
                        continue
                    rows.extend(got)
                    n += 1
                    print(f"[{n:4d}/{total}] {family:<11} {arm:<10} d={dim} s={sigma} "
                          f"seed={seed} comps "
                          f"{min(r['n_components'] for r in got)}.."
                          f"{max(r['n_components'] for r in got)} "
                          f"({time.time()-t0:.1f}s)", flush=True)

    v = verdict(rows)
    payload = {"provenance": _provenance(sys.argv),
               "config": {"families": list(FAMILIES), "arms": list(ARMS),
                          "cells": [list(c) for c in cells], "gammas": list(GAMMAS),
                          "tau_fracs": list(TAU_FRACS), "grid_n": grid_n,
                          "excluded_arms": EXCLUDED_ARMS},
               "verdict": v, "rows": rows}
    final.write_text(json.dumps(payload, indent=1))

    print(f"\n{'family':<12}{'components':>12}{'box gain':>12}{'n':>7}")
    for f, s in v["per_family"].items():
        print(f"{f:<12}{s['mean_components']:>12.2f}{s['mean_box_gain']:>12.5f}"
              f"{s['n']:>7d}")
    print(f"\nPREDICTION {'HOLDS' if v['prediction_holds'] else 'DOES NOT HOLD'}")
    print(f"  {v['note']}")
    print(f"\nwrote {final.name} · {len(rows)} rows")


if __name__ == "__main__":
    main()
