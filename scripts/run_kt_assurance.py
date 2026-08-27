"""KT · Lever A. Re-score the SAME campaigns at assurance levels above 0.95.

Registered in `docs/SPADE-ASSURANCE-CALIBRATION-SPEC.md`, frozen at `6848e2f` **before this
file existed**.

WHY THIS FORKS P8's `score()` INSTEAD OF CALLING IT
---------------------------------------------------
`run_p2_versionb_gamma.score_campaign(..., alphas=ALPHAS)` binds `ALPHAS` as a **default
argument**, which Python evaluates once at definition time. Reassigning the module attribute
therefore does nothing, and P8's own `score()` never passes `alphas` through. The ~15 lines
below mirror P8's `score()` exactly and differ in one place: `alphas=ALPHAS_KT`. The
regeneration gate on `regret`/`n_wells` at `|delta| = 0` is what catches any drift between
this copy and the original -- KR passed that gate 1000/1000 on the same construction.

WHAT IS AND IS NOT RECOMPUTED
-----------------------------
The certificate IS recomputed -- that is the experiment. No campaign is re-simulated: the
wells come from P8's own `build()`, seeded identically. The joint posterior draw is computed
once per campaign and shared across every alpha, so the whole grid costs one pass.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
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

#: Spec §2 Lever A. 0.95 is retained as the committed control, so KT-4 (Occam) is
#: computable from this file alone without reaching back to P8.
ALPHAS_KT = (0.95, 0.98, 0.99, 0.995, 0.999)

P8_COMMITTED = ROOT / "results" / "p8-certificate-families.json"
OUT_DEFAULT = ROOT / "results" / "kt-assurance.json"


def _mod(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                       # type: ignore[union-attr]
    return m


_P8 = None


def p8():
    global _P8
    if _P8 is None:
        _P8 = _mod("_kt_p8", "run_p8_certificate_families.py")
    return _P8


def committed_index() -> dict:
    rows = json.loads(P8_COMMITTED.read_text())["rows"]
    out: dict = {}
    for r in rows:
        out.setdefault((r["family"], r["instance"], r["seed"], r["arm"]), r)
    return out


def score_kt(family, instance, arm, seed, grid, X_sub, committed) -> list[dict]:
    """P8's `score()`, with `alphas=ALPHAS_KT` threaded through. Gated, not trusted."""
    from boec.replay import scored_curve

    P = p8()
    ev = P.evaluator_for(family, instance, seed)
    rec, n_wells = P.build(family, instance, arm, seed)

    with torch.no_grad():
        truth = ev.truth(grid).reshape(-1).double()
        truth_sub = ev.truth(X_sub).reshape(-1).double()

    if arm == "plate1_only":
        regret = float(rec.regret)
    else:
        mu_max = float(P.instance_optimum(instance)) if family == "hill" else 1.0
        regret = float(mu_max - scored_curve(ev, rec.X, rec.Y)[-1])

    ref = committed.get((family, instance, seed, arm))
    gate_ok = None
    if ref is not None:
        gate_ok = (abs(regret - float(ref["regret"])) == 0.0
                   and int(n_wells) == int(ref["n_wells"]))

    rows = P.p2().score_campaign(
        X=rec.X, Y=rec.Y, Yvar=rec.Yvar, orc=ev, dim=P.DIM, grid=grid, truth=truth,
        X_sub=X_sub, truth_sub=truth_sub, seed=seed, instance=instance, arm=arm,
        regret=regret, n_draws=P.N_DRAWS, alphas=ALPHAS_KT)
    for r in rows:
        r.update({"family": family, "sigma": P.SIGMA, "dim": P.DIM,
                  "n_wells": n_wells, "n_draws": P.N_DRAWS, "gate_ok": gate_ok,
                  "alphas_kt": list(ALPHAS_KT)})
    return rows


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
            "argv": list(argv), "python": sys.version.split()[0],
            "torch": torch.__version__, "botorch": botorch.__version__,
            "gpytorch": gpytorch.__version__, "numpy": numpy.__version__,
            "scipy": scipy.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--families", type=str, default="")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    from boec.norms import sobol_grid

    P = p8()
    fams = tuple(args.families.split(",")) if args.families else P.FAMILIES
    committed = committed_index()
    # Exactly P8's construction (run_p8_certificate_families.py:225-226). X_sub is its OWN
    # sobol_grid at SUBSET_N, not a prefix of `grid` -- a prefix would be a different subset
    # and would silently change every containment number.
    grid = sobol_grid(P.DIM, P.p2().GRID_N, seed=P.p2().GRID_SEED)
    X_sub = sobol_grid(P.DIM, P.p2().SUBSET_N, seed=P.p2().GRID_SEED)

    jobs = [(f, inst, arm, seed) for f in fams
            for inst, seed in P.keys_for(f, args.seeds) for arm in P.ARMS]

    if args.pilot:
        sel = jobs[:args.pilot]
        t0 = time.time()
        for f, i, a, s in sel:
            score_kt(f, i, a, s, grid, X_sub, committed)
        dt = time.time() - t0
        print(f"PILOT · {len(sel)} campaigns · {dt:.1f}s · {dt/len(sel):.1f}s each")
        print(f"projected full run: {dt/len(sel)*len(jobs)/3600:.2f} h ({len(jobs)} campaigns)")
        print("TIMING ONLY -- no outcome inspected, nothing written (spec §4)")
        return

    rows, failures, t0 = [], [], time.time()
    for n, (f, i, a, s) in enumerate(jobs, 1):
        rs = score_kt(f, i, a, s, grid, X_sub, committed)
        rows.extend(rs)
        if rs and rs[0]["gate_ok"] is False:
            failures.append({"family": f, "instance": i, "arm": a, "seed": s})
        if n % 25 == 0 or n == len(jobs):
            print(f"  {n}/{len(jobs)} · {time.time()-t0:.0f}s · {len(failures)} gate failures",
                  flush=True)
            args.out.write_text(json.dumps(
                {"status": "PARTIAL", "n_campaigns": n, "gate_failures": failures,
                 "alphas_kt": list(ALPHAS_KT), "provenance": _provenance(sys.argv),
                 "rows": rows}, indent=1))

    args.out.write_text(json.dumps(
        {"status": "COMPLETE" if not failures else "GATE_FAILURES",
         "spec": "docs/SPADE-ASSURANCE-CALIBRATION-SPEC.md",
         "n_campaigns": len(jobs), "gate_failures": failures,
         "alphas_kt": list(ALPHAS_KT), "provenance": _provenance(sys.argv),
         "rows": rows}, indent=1))
    print(f"\nwrote {args.out} · {len(rows)} rows · {len(failures)} gate failures")


if __name__ == "__main__":
    main()
