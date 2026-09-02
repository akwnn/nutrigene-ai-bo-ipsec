"""KV · prospective test of Plate-2 targeting on the CERTIFICATE deliverable.

Registered in `docs/SPADE-PLATE2-CERTIFICATE-SPEC.md`, frozen at `1df991a` **before this file
existed**.

WHAT IS PROSPECTIVE HERE
------------------------
Plate 2's wells are generated live, from each arm's frozen rule applied to that campaign's own
plate-1 fit. `spade_cert_rho95` has never been run before, so none of its rows exist anywhere.
This is not a re-score.

THE FOUR ARMS (spec §4)
-----------------------
    spade_cert_rho95   batch_lse_rho at CERT_RHO=0.95  -- the new arm
    versionb           Bryan's straddle (= rho 0.5)    -- current targeting
    versionb_random    uniform random                  -- THE CAUSAL CONTROL
    plate1_only        48 wells, one round             -- architecture control

ARM-DISTINCTNESS IS ENFORCED, NOT ASSUMED (spec §4)
---------------------------------------------------
Every campaign asserts that `spade_cert_rho95` and `versionb` selected **different** plate-2
wells. Two arms silently identical is the failure mode a `rho` parameter most invites, and this
repository has shipped three errata of exactly that shape. A collision **pauses KV** and is
reported, not patched.

CHECKPOINTS, BECAUSE KU TAUGHT ME
---------------------------------
KU wrote its JSON once at the end and ran 5x over its pilot estimate; a crash at hour 16 would
have lost everything (`SPADE-PREVALENCE-MATCHED-SPEC.md` §5c). This runner writes a PARTIAL
payload every 10 campaigns and is launched with `-u`.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software" / "src"))

ARMS = ("spade_cert_rho95", "versionb", "versionb_random", "plate1_only")
MODE = {"spade_cert_rho95": "cert", "versionb": "lse", "versionb_random": "random"}
OUT_DEFAULT = ROOT / "research" / "results" / "kv-plate2-certificate.json"


def _mod(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                       # type: ignore[union-attr]
    return m


_P8 = _VB = None


def p8():
    global _P8
    if _P8 is None:
        _P8 = _mod("_kv_p8", "run_p8_certificate_families.py")
    return _P8


def vb():
    global _VB
    if _VB is None:
        _VB = _mod("_kv_vb", "run_versionb.py")
    return _VB


def build(family: str, arm: str, seed: int):
    """One 48-well campaign under `arm`'s own rule. `plate1_only` is 48 LHS wells, one round."""
    from boec.replay import regenerate

    P, V = p8(), vb()
    if arm == "plate1_only":
        rec = regenerate(family, P.DIM, P.SIGMA, seed, "lhs", family=family)
        return rec.X, rec.Y, rec.Yvar, None
    orc = P.evaluator_for(family, family, seed)
    X, Y, Yvar, diag = V._two_plate(orc, P.DIM, seed, 1.0, MODE[arm])
    return X, Y, Yvar, diag


def score(family: str, seed: int, arm: str, grid, X_sub, tau_by_p) -> list[dict]:
    from boec.replay import scored_curve

    P = p8()
    p2 = P.p2()
    ev = P.evaluator_for(family, family, seed)
    X, Y, Yvar, _ = build(family, arm, seed)

    with torch.no_grad():
        truth_sub = ev.truth(X_sub).reshape(-1).double()

    regret = float(1.0 - scored_curve(ev, X, Y)[-1])

    from boec.replay import unit_bounds
    from boec.surrogate import build_gp
    model = build_gp(X, Y, Yvar, unit_bounds(P.DIM))
    with torch.no_grad():
        post = model.posterior(X_sub)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], P.N_DRAWS, generator=g, dtype=torch.double)
        draws = (post.mean.reshape(-1, 1).double() + L @ z).T

    rows = []
    for gamma in p2.GAMMAS:
        for p_val, tau in tau_by_p.items():
            # KV-4 needs MAP error, and the certificate-only path does not produce it.
            # Computed here from the draws already in hand, on the 2,000-point subset:
            #   p(x) = fraction of joint draws clearing tau; fitted set = {p >= 0.5};
            #   error = |fitted set XOR true set| / N.
            # Named `map_total_error_vol_sub` and NOT `total_error_vol`, because the
            # committed column of that name is computed on the 20,000-point grid and the two
            # are not interchangeable. KV-4 is a WITHIN-KV arm comparison, so a subset-
            # resolution map error is sufficient for it and comparability with P8 is not
            # required -- but conflating the names would invite exactly that mistake later.
            with torch.no_grad():
                pmap = (draws >= tau).double().mean(dim=0)
                fitted = pmap >= 0.5
                true_set = truth_sub >= tau
                map_err = float((fitted ^ true_set).double().mean())
            rows.append({"map_total_error_vol_sub": map_err,
                         "family": family, "seed": seed, "arm": arm, "dim": P.DIM,
                         "sigma": P.SIGMA, "n_wells": int(X.shape[0]), "regret": regret,
                         "gamma": gamma, "p_value": p_val, "tau": tau,
                         "n_draws": P.N_DRAWS,
                         **p2.vorobev_columns(draws, truth_sub, tau, p2.ALPHAS)})
    del model, draws
    gc.collect()
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
            "git_dirty": bool(_git("status", "--porcelain")), "argv": list(argv),
            "python": sys.version.split()[0], "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--families", type=str, default="levy,rosenbrock")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    from boec.designspace import tau_quantile
    from boec.norms import sobol_grid

    P = p8()
    p2 = P.p2()
    fams = tuple(args.families.split(","))
    grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    P_VALUES = (0.30, 0.10, 0.03, 0.01)

    tau_by_family = {}
    for fam in fams:
        ev0 = P.evaluator_for(fam, fam, 0)
        with torch.no_grad():
            t = ev0.truth(grid).reshape(-1).double()
        tau_by_family[fam] = {p: float(tau_quantile(t, p)) for p in P_VALUES}

    seeds = range(args.pilot if args.pilot else args.seeds)
    jobs = [(f, s) for f in fams for s in seeds]

    rows, collisions, t0 = [], [], time.time()
    for n, (fam, seed) in enumerate(jobs, 1):
        # KV §4: arm distinctness, enforced per campaign.
        Xc, *_ = build(fam, "spade_cert_rho95", seed)
        Xl, *_ = build(fam, "versionb", seed)
        if torch.equal(Xc[vb().N_PLATE1:], Xl[vb().N_PLATE1:]):
            collisions.append({"family": fam, "seed": seed})

        for arm in ARMS:
            rows.extend(score(fam, seed, arm, grid, X_sub, tau_by_family[fam]))

        if args.pilot:
            continue
        if n % 10 == 0 or n == len(jobs):
            el = time.time() - t0
            print(f"[{n:3d}/{len(jobs)}] {fam:<11} rows={len(rows):>6} "
                  f"collisions={len(collisions)} ({el/60:.1f}m, "
                  f"{el/(n*len(ARMS)):.0f}s/campaign)", flush=True)
            args.out.write_text(json.dumps(
                {"status": "PARTIAL", "n_done": n, "arm_collisions": collisions,
                 "provenance": _provenance(sys.argv), "rows": rows}, indent=1))

    if args.pilot:
        dt = time.time() - t0
        nc = len(jobs) * len(ARMS)
        full = len(fams) * args.seeds * len(ARMS)
        print(f"PILOT · {nc} campaigns · {dt:.1f}s · {dt/nc:.1f}s each")
        print(f"arm collisions (cert vs lse): {len(collisions)} / {len(jobs)}")
        print(f"projected full run ({full} campaigns): {dt/nc*full/3600:.2f} h")
        if dt / nc * full / 3600 > 8.0:
            print("EXCEEDS spec §7's 8-hour ceiling -- reduce seeds and RECORD it before "
                  "running, per KU §5/§5b.")
        print("TIMING + COLLISION CHECK ONLY -- nothing written")
        return

    args.out.write_text(json.dumps(
        {"status": "COMPLETE" if not collisions else "ARM_COLLISIONS",
         "spec": "docs/SPADE-PLATE2-CERTIFICATE-SPEC.md",
         "n_campaigns": len(jobs) * len(ARMS), "arm_collisions": collisions,
         "cert_rho": vb().CERT_RHO, "provenance": _provenance(sys.argv), "rows": rows},
        indent=1))
    print(f"\nwrote {args.out} · {len(rows)} rows · {len(collisions)} arm collisions")
    if collisions:
        print("ARM COLLISIONS -- KV paused per spec §4. Reported, not patched.")


if __name__ == "__main__":
    main()
