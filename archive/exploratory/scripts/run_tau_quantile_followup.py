"""tau-as-quantile follow-up. Pre-registered: docs/SPADE-TAU-QUANTILE-SPEC.md.

Read-only with respect to every frozen file. `run_p2_versionb_gamma.py` and
`run_p8_certificate_families.py` are loaded dynamically (the same `_mod` pattern P8
itself uses to reuse P2) and nothing on either file is edited; `P2.tau_for` is
monkeypatched at runtime, exactly as `run_kf3_followup_benchmark.py` monkeypatched
`run_final_spade_benchmark.build` for the KF-3 follow-up. Only `ackley` and
`hartmann6` are re-scored -- the two families whose registered grid (a fixed
fraction of peak height) makes them near-totally empty, per FINDINGS-SPADE.md sec 41
and COVERAGE-MATRIX.md sec B1. `hill`/`levy`/`rosenbrock` are not re-run (spec sec 4).

    .venv/bin/python -u scripts/run_tau_quantile_followup.py --pilot
    .venv/bin/python -u scripts/run_tau_quantile_followup.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import tau_max as _tau_max_fn, tau_quantile  # noqa: E402
from boec.replay import family_evaluator                            # noqa: E402


def _mod(alias: str, filename: str):
    spec = importlib.util.spec_from_file_location(alias, ROOT / "scripts" / filename)
    m = importlib.util.module_from_spec(spec)
    sys.modules[alias] = m
    spec.loader.exec_module(m)
    return m


P8 = _mod("_tq_p8", "run_p8_certificate_families.py")
#: The SAME module instance `P8.score()` calls into internally (`P8.p2()`, cached) --
#: not a separately-loaded copy. Patching a second, independent load of
#: run_p2_versionb_gamma.py would silently do nothing, since `P8.score` resolves
#: `tau_for` through its own cached `_P2`, not through this module.
P2 = P8.p2()

FAMILIES = ("ackley", "hartmann6")
ARMS = P8.ARMS
DIM, SIGMA = P8.DIM, P8.SIGMA
N_DRAWS = P8.N_DRAWS
#: Registered p-grid (docs/SPADE-TAU-QUANTILE-SPEC.md sec 2) -- repurposes
#: `score_campaign`'s `tau_fracs` keyword; rows are relabelled `p_value` below so
#: nobody downstream mistakes these for the old tau_frac*tau_max definition.
P_VALUES = (0.30, 0.10, 0.03, 0.01)

OUT = ROOT / "results" / "tau-quantile-followup.json"
P8_COMMITTED = ROOT / "results" / "p8-certificate-families.json"


def _p8_committed_index() -> dict:
    d = json.loads(P8_COMMITTED.read_text())
    return {(r.get("family"), r.get("seed"), r.get("arm")): r for r in d["rows"]
            if r.get("family") in FAMILIES}


def _make_patched_tau_for(tau_by_p: dict):
    """Same signature as P2.tau_for(gamma, tau_frac, sigma_rel) -> (tau, tau_max).

    Ignores `gamma` and `sigma_rel` for the tau value itself (quantile tau depends
    only on the true response distribution, not on assurance or noise) but still
    returns tau_max for the row's `tau_max` column, so downstream columns that
    reference it are not silently `None`.
    """
    def _tau_for(gamma: float, p: float, sigma_rel: float):
        return tau_by_p[p], _tau_max_fn(gamma, sigma_rel)
    return _tau_for


def score_family(family: str, grid, X_sub, seeds, committed_index: dict,
                  gate_fail: list) -> tuple[list, dict]:
    """Mirrors `P8.score()` exactly (same campaign build, same regret formula), but
    calls `P2.score_campaign` DIRECTLY with `tau_fracs=P_VALUES` passed explicitly.

    `P8.score()` cannot be reused as-is: it calls `score_campaign(...)` without a
    `tau_fracs=` argument, so Python falls back to `score_campaign`'s *default*
    parameter value -- which was bound to the original `TAU_FRACS` tuple at function
    DEFINITION time, not looked up fresh at call time. Patching `P2.tau_for` alone is
    not enough; the p-values must be threaded through explicitly or the old
    `tau_frac` grid silently keeps running. (Caught by a smoke test before any
    registered row was written -- see commit log.)
    """
    ev0 = family_evaluator(family, DIM, SIGMA, 0)
    with torch.no_grad():
        truth = ev0.truth(grid).reshape(-1).double()
        truth_sub = ev0.truth(X_sub).reshape(-1).double()
    tau_by_p = {p: tau_quantile(truth, p) for p in P_VALUES}
    P2.tau_for = _make_patched_tau_for(tau_by_p)

    rows = []
    for seed in seeds:
        ev = P8.evaluator_for(family, family, seed)
        for arm in ARMS:
            rec, n_wells = P8.build(family, family, arm, seed)
            if arm == "plate1_only":
                regret = float(rec.regret)
            else:
                regret = float(1.0 - P8.scored_curve(ev, rec.X, rec.Y)[-1])
            got = P2.score_campaign(
                X=rec.X, Y=rec.Y, Yvar=rec.Yvar, orc=ev, dim=DIM, grid=grid,
                truth=truth, X_sub=X_sub, truth_sub=truth_sub, seed=seed,
                instance=family, arm=arm, regret=regret, n_draws=N_DRAWS,
                tau_fracs=P_VALUES)
            for r in got:
                r.update({"family": family, "sigma": SIGMA, "dim": DIM,
                          "n_wells": n_wells, "n_draws": N_DRAWS})
            ref = committed_index.get((family, seed, arm))
            if ref is not None:
                for col in ("regret", "n_wells"):
                    d = abs(float(got[0][col]) - float(ref[col]))
                    if d > 0.0:
                        gate_fail.append({"family": family, "seed": seed, "arm": arm,
                                          "column": col, "committed": ref[col],
                                          "regenerated": got[0][col], "abs_delta": d})
            for r in got:
                r["p_value"] = r.pop("tau_frac")
                r["tau_definition"] = "quantile"
            rows.extend(got)
    return rows, tau_by_p


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    return {"git_sha": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true",
                     help="time 5 campaigns only, write nothing registered")
    ap.add_argument("--seeds", type=int, default=50)
    args = ap.parse_args()

    from boec.norms import sobol_grid
    grid = sobol_grid(DIM, P2.GRID_N, seed=P2.GRID_SEED)
    X_sub = sobol_grid(DIM, P2.SUBSET_N, seed=P2.GRID_SEED)

    if args.pilot:
        t0 = time.time()
        _, tau_by_p = score_family("ackley", grid, X_sub, range(5), {}, [])
        elapsed = time.time() - t0
        n_campaigns = 5 * len(ARMS)
        print(f"pilot: {n_campaigns} campaigns (5 seeds x {len(ARMS)} arms) "
              f"in {elapsed:.1f}s", flush=True)
        print(f"ackley tau_by_p: {tau_by_p}")
        per_campaign = elapsed / n_campaigns
        print(f"\nmean {per_campaign:.1f}s/campaign "
              f"(P8's own log: ~20-30s/campaign)")
        est_total = per_campaign * len(FAMILIES) * len(ARMS) * args.seeds
        print(f"estimated full run ({len(FAMILIES)} families x {len(ARMS)} arms x "
              f"{args.seeds} seeds = {len(FAMILIES)*len(ARMS)*args.seeds} campaigns): "
              f"{est_total/60:.0f} min")
        if per_campaign > 60.0:
            print("\nPILOT EXCEEDS spec sec 6's 2x-estimate ceiling (60s) -- "
                  "STOP, do not launch the full run without reporting this first.")
        return

    committed_index = _p8_committed_index()
    seeds = range(args.seeds)
    total = len(FAMILIES) * len(ARMS) * args.seeds
    print(f"tau-quantile follow-up: families={FAMILIES} arms={ARMS} "
          f"p_values={P_VALUES} n_draws={N_DRAWS}")
    print(f"{total} campaigns\n")

    rows, gate_fail, taus_by_family, n = [], [], {}, 0
    partial = OUT.with_suffix(OUT.suffix + ".partial")
    t0 = time.time()
    for family in FAMILIES:
        fam_rows, tau_by_p = score_family(family, grid, X_sub, seeds, committed_index, gate_fail)
        taus_by_family[family] = {str(p): tau_by_p[p] for p in P_VALUES}
        rows.extend(fam_rows)
        n += len(seeds) * len(ARMS)
        el = time.time() - t0
        print(f"[{n:4d}/{total}] {family:<11} done rows={len(rows):>6} "
              f"gate_fail={len(gate_fail)} ({el/60:.1f}m)", flush=True)
        partial.write_text(json.dumps(
            {"status": "partial", "keys_present": n, "keys_expected": total,
             "provenance": _provenance(sys.argv),
             "config": {"families": list(FAMILIES), "arms": list(ARMS), "dim": DIM,
                        "sigma": SIGMA, "n_seeds": len(seeds), "n_draws": N_DRAWS,
                        "p_values": list(P_VALUES),
                        "gate_note": "regret/n_wells gated against P8's committed "
                                     "rows at |delta|=0 -- same campaigns, only tau "
                                     "changed"},
             "tau_by_family": taus_by_family,
             "gate_failures": gate_fail, "rows": rows}, indent=1))
    payload = json.loads(partial.read_text())
    payload["status"] = "COMPLETE"
    OUT.write_text(json.dumps(payload, indent=1))
    partial.unlink(missing_ok=True)
    print(f"\ngate failures: {len(gate_fail)}")
    print(f"wrote {OUT.name} - {len(rows)} rows")


if __name__ == "__main__":
    main()
