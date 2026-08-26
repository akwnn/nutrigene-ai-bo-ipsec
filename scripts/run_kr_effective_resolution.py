"""KR · effective resolution. Regenerate wells, refit the GP, read ARD lengthscales.

Registered in `docs/SPADE-EFFECTIVE-RESOLUTION-SPEC.md`, frozen at commit `7ae6fc6`
**before this file existed**.

WHAT THIS DOES NOT DO
---------------------
No campaign is simulated and no certificate is recomputed. The `ce_*` columns are already
committed in `results/p8-certificate-families.json`. This script regenerates each campaign's
**wells only**, through P8's own `build()`, fits the GP with P8's exact `build_gp` settings,
and reads the fitted ARD lengthscales. The expensive P8 step -- the 4,096-draw joint
posterior and its Cholesky -- is never touched.

THE GATE
--------
Every regenerated campaign's `regret` and `n_wells` must reproduce its committed P8 row at
`|delta| = 0` before its lengthscale is used, matching the gates
`SPADE-CALIBRATION-FIX-SPEC.md` §3b and `SPADE-TAU-QUANTILE-SPEC.md` §3 already apply. A
campaign that fails is **reported, not patched**, and KR pauses -- a builder that no longer
reproduces its committed column is a separate finding, not a nuisance to route around.
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

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

P8_COMMITTED = ROOT / "results" / "p8-certificate-families.json"
OUT_DEFAULT = ROOT / "results" / "ks-self-calibration.json"


def _mod(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                       # type: ignore[union-attr]
    return m


_P8 = None


def p8():
    """P8 imported read-only. It owns the campaign construction; KR must not fork it."""
    global _P8
    if _P8 is None:
        _P8 = _mod("_kr_p8", "run_p8_certificate_families.py")
    return _P8


def ard_lengthscales(model) -> list[float]:
    """The fitted ARD lengthscales, one per dimension.

    `build_gp`'s default is `use_scale_kernel=True`, so the ARD Matern sits under a
    ScaleKernel. Falling back to `covar_module` directly keeps this working if that default
    ever changes, rather than reading an outputscale as if it were a lengthscale.
    """
    cm = model.covar_module
    k = getattr(cm, "base_kernel", cm)
    ls = k.lengthscale.detach().reshape(-1).double()
    return [float(x) for x in ls]


def committed_index() -> dict:
    """`(family, instance, seed, arm) -> row` from P8, for the campaign-level gate."""
    rows = json.loads(P8_COMMITTED.read_text())["rows"]
    out: dict = {}
    for r in rows:
        out.setdefault((r["family"], r["instance"], r["seed"], r["arm"]), r)
    return out


def one_campaign(family: str, instance: str, arm: str, seed: int, committed: dict) -> dict:
    """Regenerate one campaign's wells, refit, gate, and return its lengthscale row."""
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    P = p8()
    rec, n_wells = P.build(family, instance, arm, seed)

    if arm == "plate1_only":
        regret = float(rec.regret)
    else:
        ev = P.evaluator_for(family, instance, seed)
        mu_max = float(P.instance_optimum(instance)) if family == "hill" else 1.0
        regret = float(mu_max - scored_curve(ev, rec.X, rec.Y)[-1])

    ref = committed.get((family, instance, seed, arm))
    gate_ok, d_regret, d_wells = None, None, None
    if ref is not None:
        d_regret = abs(regret - float(ref["regret"]))
        d_wells = abs(int(n_wells) - int(ref["n_wells"]))
        gate_ok = (d_regret == 0.0) and (d_wells == 0)

    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(P.DIM))
    ell = ard_lengthscales(model)
    k_tail, k_mean = loo_calibration(model)

    return {"family": family, "instance": instance, "arm": arm, "seed": seed,
            "dim": P.DIM, "sigma": P.SIGMA, "n_wells": int(n_wells), "regret": regret,
            "lengthscales": ell, "kappa_tail": k_tail, "kappa_mean": k_mean,
            "gate_ok": gate_ok,
            "gate_delta_regret": d_regret, "gate_delta_wells": d_wells}


def loo_calibration(model) -> tuple[float, float]:
    """`(kappa_tail, kappa_mean)` from the fitted model's own leave-one-out residuals.

    Everything is taken in the model's INTERNAL (transformed) space -- `train_targets` and
    `covar_module` are both post-transform, so mixing an untransformed `Y` in here would
    standardise the numerator and not the denominator and report nonsense.

    The covariance passed to `loo_residuals` includes the likelihood's noise on the
    diagonal, per `docs/SPADE-SELF-CALIBRATION-SPEC.md` §4; `loo_residuals` rejects a
    noise-free matrix on its condition number rather than returning round-off.
    """
    from boec.selfcalib import calibration_inflation, calibration_tail, loo_residuals

    with torch.no_grad():
        Xtr = model.train_inputs[0]
        ytr = model.train_targets.reshape(-1).double()
        Kf = model.covar_module(Xtr).to_dense().double().reshape(ytr.numel(), -1)
        noise = model.likelihood.noise.reshape(-1).double()
        if noise.numel() == 1:
            noise = noise.expand(ytr.numel())
        K = (Kf + torch.diag(noise)).cpu().numpy()
        m = model.mean_module(Xtr).reshape(-1).double().cpu().numpy()
        y = ytr.cpu().numpy()

    mu_c, var_loo = loo_residuals(K, y - m)
    mu_loo, sd_loo = mu_c + m, np.sqrt(var_loo)
    return (calibration_tail(y, mu_loo, sd_loo),
            calibration_inflation(y, mu_loo, sd_loo))


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
    ap.add_argument("--pilot", type=int, default=0,
                    help="firewalled timing pilot: run N campaigns, report wall clock "
                         "only, write nothing (spec §4)")
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--families", type=str, default="")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    P = p8()
    fams = tuple(args.families.split(",")) if args.families else P.FAMILIES
    committed = committed_index()

    jobs: list[tuple[str, str, str, int]] = []
    for fam in fams:
        for instance, seed in P.keys_for(fam, args.seeds):
            for arm in P.ARMS:
                jobs.append((fam, instance, arm, seed))

    if args.pilot:
        jobs = jobs[:args.pilot]
        t0 = time.time()
        for fam, inst, arm, seed in jobs:
            one_campaign(fam, inst, arm, seed, committed)
        dt = time.time() - t0
        print(f"PILOT · {len(jobs)} campaigns · {dt:.1f}s total · {dt/len(jobs):.2f}s each")
        print(f"projected full run ({len(fams)} families): "
              f"{dt/len(jobs) * (len(P.ARMS) * sum(len(P.keys_for(f, args.seeds)) for f in fams)) / 60:.1f} min")
        print("TIMING ONLY -- no outcome inspected, nothing written (spec §4)")
        return

    rows, failures = [], []
    t0 = time.time()
    for i, (fam, inst, arm, seed) in enumerate(jobs, 1):
        r = one_campaign(fam, inst, arm, seed, committed)
        rows.append(r)
        if r["gate_ok"] is False:
            failures.append({k: r[k] for k in
                             ("family", "instance", "arm", "seed",
                              "gate_delta_regret", "gate_delta_wells")})
        if i % 50 == 0 or i == len(jobs):
            print(f"  {i}/{len(jobs)} · {time.time()-t0:.0f}s · "
                  f"{len(failures)} gate failures", flush=True)

    payload = {"status": "COMPLETE" if not failures else "GATE_FAILURES",
               "spec": "docs/SPADE-EFFECTIVE-RESOLUTION-SPEC.md",
               "n_campaigns": len(rows), "gate_failures": failures,
               "provenance": _provenance(sys.argv), "rows": rows}
    args.out.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {args.out} · {len(rows)} campaigns · {len(failures)} gate failures")
    if failures:
        print("GATE FAILURES PRESENT -- KR is paused per spec §4. Reported, not patched.")


if __name__ == "__main__":
    main()
