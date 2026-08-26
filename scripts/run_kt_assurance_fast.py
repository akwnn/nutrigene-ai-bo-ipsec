"""KT · Lever A, certificate-only scorer with a reproduction gate.

Registered in `docs/SPADE-ASSURANCE-CALIBRATION-SPEC.md`, frozen at `6848e2f`.

WHY A SECOND RUNNER
-------------------
`run_kt_assurance.py`'s firewalled pilot measured **113.2 s/campaign -> 31.4 h**, over the
8-hour ceiling spec §4 sets. §4's remedy is to cut seeds and report the reduced power. Reading
`run_p2_versionb_gamma.score_campaign` shows a better option that costs no power at all: the
certificate columns come from `vorobev_columns(draws, truth_sub, tau, alphas)`, and `draws` is
the joint posterior on the **2,000-point subset**. Everything else in that function -- the
chunked posterior over the 20,000-point grid, `sup_err`, `grid_r2`, the predictive and latent
probability maps, `inscribed_box_from_mask`, Brier/AUC/AUPRC, all of it recomputed for each of
24 `(gamma, tau_frac)` cells -- produces **map** columns that KT does not read.

This runner computes the certificate path only. The draw construction below is copied line for
line from `score_campaign` (the `1e-8` jitter, the Cholesky, the seeded generator, the
`randn(n, n_draws)` fill order) because any deviation silently changes every containment number.

THE GATE THAT MAKES THE FORK SAFE
---------------------------------
`ALPHAS_KT` retains **0.95**, which P8 already committed. Every campaign's recomputed
`ce_vol_0.95` / `ce_empty_0.95` / `ce_contain_0.95` / `ce_empirical_0.95` must reproduce P8's
committed row at `|delta| = 0`. A fork that reproduces the committed column at the shared alpha
is measuring the same estimator at the new ones; a fork that does not is **reported and the run
paused**, not patched. `regret` and `n_wells` are gated as well, exactly as KR gated them
1000/1000.
"""
from __future__ import annotations

import argparse
import gc
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

ALPHAS_KT = (0.95, 0.98, 0.99, 0.995, 0.999)
GATE_ALPHA = "0.95"                       # the shared level P8 already committed

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
        _P8 = _mod("_ktf_p8", "run_p8_certificate_families.py")
    return _P8


def committed_index() -> dict:
    out: dict = {}
    for r in json.loads(P8_COMMITTED.read_text())["rows"]:
        out[(r["family"], r["instance"], r["seed"], r["arm"],
             r["gamma"], r["tau_frac"])] = r
    return out


def joint_draws(model, X_sub, seed: int, n_draws: int):
    """Copied line for line from `score_campaign`. Deviating changes every number."""
    with torch.no_grad():
        post = model.posterior(X_sub)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], n_draws, generator=g, dtype=torch.double)
        return (post.mean.reshape(-1, 1).double() + L @ z).T


def score_kt(family, instance, arm, seed, X_sub, committed) -> tuple[list[dict], list[dict]]:
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    P = p8()
    p2 = P.p2()
    ev = P.evaluator_for(family, instance, seed)
    rec, n_wells = P.build(family, instance, arm, seed)

    with torch.no_grad():
        truth_sub = ev.truth(X_sub).reshape(-1).double()

    if arm == "plate1_only":
        regret = float(rec.regret)
    else:
        mu_max = float(P.instance_optimum(instance)) if family == "hill" else 1.0
        regret = float(mu_max - scored_curve(ev, rec.X, rec.Y)[-1])

    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(P.DIM))
    draws = joint_draws(model, X_sub, seed, P.N_DRAWS)

    rows, breaks = [], []
    for gamma in p2.GAMMAS:
        for tf in p2.TAU_FRACS:
            tau, tmax = p2.tau_for(gamma, tf, ev.sigma_rel)
            cols = p2.vorobev_columns(draws, truth_sub, tau, ALPHAS_KT)
            row = {"family": family, "instance": instance, "arm": arm, "seed": seed,
                   "dim": P.DIM, "sigma": P.SIGMA, "n_wells": int(n_wells),
                   "regret": regret, "gamma": gamma, "tau_frac": tf, "tau": tau,
                   "tau_max": tmax, "n_draws": P.N_DRAWS, **cols}

            ref = committed.get((family, instance, seed, arm, gamma, tf))
            if ref is not None:
                bad = {}
                if abs(regret - float(ref["regret"])) != 0.0:
                    bad["regret"] = [regret, ref["regret"]]
                if int(n_wells) != int(ref["n_wells"]):
                    bad["n_wells"] = [n_wells, ref["n_wells"]]
                for k in (f"ce_vol_{GATE_ALPHA}", f"ce_empty_{GATE_ALPHA}",
                          f"ce_contain_{GATE_ALPHA}", f"ce_empirical_{GATE_ALPHA}"):
                    a, b = row.get(k), ref.get(k)
                    if isinstance(a, bool) or isinstance(b, bool):
                        if bool(a) != bool(b):
                            bad[k] = [a, b]
                    elif a is None or b is None:
                        continue
                    elif (a != a) and (b != b):        # both NaN: agree
                        continue
                    elif float(a) != float(b):
                        bad[k] = [a, b]
                row["gate_ok"] = not bad
                if bad:
                    breaks.append({"family": family, "instance": instance, "arm": arm,
                                   "seed": seed, "gamma": gamma, "tau_frac": tf,
                                   "mismatch": bad})
            rows.append(row)

    del model, draws
    gc.collect()
    return rows, breaks


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
    X_sub = sobol_grid(P.DIM, P.p2().SUBSET_N, seed=P.p2().GRID_SEED)

    jobs = [(f, inst, arm, seed) for f in fams
            for inst, seed in P.keys_for(f, args.seeds) for arm in P.ARMS]

    if args.pilot:
        sel = jobs[:args.pilot]
        t0 = time.time()
        nb = 0
        for f, i, a, s in sel:
            _, br = score_kt(f, i, a, s, X_sub, committed)
            nb += len(br)
        dt = time.time() - t0
        print(f"PILOT · {len(sel)} campaigns · {dt:.1f}s · {dt/len(sel):.1f}s each")
        print(f"projected full run: {dt/len(sel)*len(jobs)/3600:.2f} h ({len(jobs)} campaigns)")
        print(f"REPRODUCTION GATE vs committed alpha={GATE_ALPHA}: "
              f"{nb} mismatching rows out of {len(sel)*24}")
        print("timing + gate only -- no KT outcome inspected, nothing written")
        return

    rows, breaks, t0 = [], [], time.time()
    for n, (f, i, a, s) in enumerate(jobs, 1):
        rs, br = score_kt(f, i, a, s, X_sub, committed)
        rows.extend(rs)
        breaks.extend(br)
        if n % 25 == 0 or n == len(jobs):
            print(f"  {n}/{len(jobs)} · {time.time()-t0:.0f}s · {len(breaks)} gate breaks",
                  flush=True)
    payload = {"status": "COMPLETE" if not breaks else "GATE_FAILURES",
               "spec": "docs/SPADE-ASSURANCE-CALIBRATION-SPEC.md",
               "n_campaigns": len(jobs), "gate_failures": breaks[:200],
               "n_gate_failures": len(breaks), "alphas_kt": list(ALPHAS_KT),
               "provenance": _provenance(sys.argv), "rows": rows}
    args.out.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {args.out} · {len(rows)} rows · {len(breaks)} gate breaks")
    if breaks:
        print("GATE BREAKS PRESENT -- KT paused per spec §4. Reported, not patched.")


if __name__ == "__main__":
    main()
