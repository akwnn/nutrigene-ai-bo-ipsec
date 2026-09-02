"""SPADE's certificate on the published Hall & Ogle 2025 iPSC-EC ECM data.

**The gap this closes.** Every containment number in this project comes from a synthetic
test function (ackley, hartmann6, levy, rosenbrock). `run_replay_hall_ogle.py` replays the
real study but measures optimisation only -- it never certifies. So SPADE's certificate had
never been applied to real cell-manufacturing data at all.

Stage 1 is a 6-factor ECM screen (collagen I, collagen IV, laminin 111/411/511,
fibronectin) at +/-1, 23 usable runs, each with a published response SD. That SD is the
honest noise and it is brutal: several runs have CV above 100%.

The question a process-development lab asks: **which ECM compositions can be certified to
exceed a given response?** `c` is calibrated on this data by leave-one-out, exactly as
`calibrate_real_assay_loo.py` does for the in-house assay -- never imported from
simulation, which `SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10 showed does not transfer.
"""
from __future__ import annotations

import csv, sys, warnings
from pathlib import Path

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software" / "src"))

SRC = ROOT / "research/data/published/hall_ogle_2025_stage1.csv"
FACTORS = ("c", "civ", "ln111", "ln411", "ln511", "fn")
N_DRAWS = 4000


def load():
    X, Y, S = [], [], []
    for r in csv.DictReader(open(SRC)):
        if r.get("flagged", "").strip().lower() == "true":
            continue                                  # unreadable from the figure
        if not r["response"] or not r["response_sd"]:
            continue
        # +/-1 coded factors -> unit cube, the space every other module works in
        X.append([(float(r[f]) + 1.0) / 2.0 for f in FACTORS])
        Y.append(float(r["response"]))
        S.append(float(r["response_sd"]))
    return (torch.tensor(X, dtype=torch.double),
            torch.tensor(Y, dtype=torch.double).unsqueeze(-1),
            torch.tensor(S, dtype=torch.double).unsqueeze(-1) ** 2)


def loo_c(X, Y, Yvar, bounds, use_meanmarg: bool):
    """Calibrate the inflation on THIS data. Never imported from simulation."""
    from boec.meanmarg import mean_marginalised_covariance
    from boec.selfcalib import calibration_inflation
    from boec.surrogate import build_gp

    n = X.shape[0]
    mus, sds, ys = [], [], []
    for i in range(n):
        keep = [j for j in range(n) if j != i]
        m = build_gp(X[keep], Y[keep], Yvar[keep], bounds)
        xi = X[i:i + 1]
        with torch.no_grad():
            p = m.posterior(xi)
            var = float(p.variance.reshape(-1)[0])
            mu = float(p.mean.reshape(-1)[0])
        if use_meanmarg:
            var = float(mean_marginalised_covariance(m, xi).reshape(-1)[0])
        mus.append(mu); sds.append((var + float(Yvar[i])) ** 0.5); ys.append(float(Y[i]))
    mus, sds, ys = np.array(mus), np.array(sds), np.array(ys)
    z = (ys - mus) / sds
    return calibration_inflation(ys, mus, sds), float(np.std(z, ddof=1)), \
        float(np.mean(np.abs(z) <= 1.0))


def main():
    from boec.meanmarg import mean_marginalised_covariance
    from boec.surrogate import build_gp
    from boec.topk import certified_topk
    from boec.vorobev import conservative_estimate

    X, Y, Yvar = load()
    n, d = X.shape
    sd = Yvar.sqrt().reshape(-1)
    print(f"Hall & Ogle 2025 stage 1: {n} ECM compositions, {d} factors")
    print(f"  response {Y.min():.3f}..{Y.max():.3f} (median {Y.median():.3f})")
    print(f"  published SD {sd.min():.3f}..{sd.max():.3f}; "
          f"median CV {100*float((sd/Y.reshape(-1)).median()):.0f}%")
    print(f"  signal var {float(Y.var()):.3f} vs mean noise var "
          f"{float(Yvar.mean()):.3f}  -> SNR {float(Y.var()/Yvar.mean()):.2f}\n")

    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    for mm in (False, True):
        c, zsd, cov68 = loo_c(X, Y, Yvar, bounds, mm)
        print(f"  LOO calibration [{'meanmarg' if mm else 'raw':>8}]: "
              f"c = {c:.3f}   residual sd {zsd:.3f}   coverage@68% {cov68:.3f}")
    print()

    m = build_gp(X, Y, Yvar, bounds)
    g = torch.Generator().manual_seed(0)
    cand = torch.rand(3000, d, generator=g, dtype=torch.double)
    with torch.no_grad():
        post = m.posterior(cand)
        mean = post.mean.reshape(-1, 1).double()
        raw = post.mvn.covariance_matrix.double()
    mmcov = mean_marginalised_covariance(m, cand)
    print(f"posterior sd: raw {raw.diagonal().sqrt().mean():.4f}  "
          f"-> mean-marginalised {mmcov.diagonal().sqrt().mean():.4f}  "
          f"({mmcov.diagonal().sqrt().mean()/raw.diagonal().sqrt().mean():.1f}x)\n")

    I = torch.eye(len(cand), dtype=torch.double)
    z = torch.randn(len(cand), N_DRAWS,
                    generator=torch.Generator().manual_seed(0), dtype=torch.double)
    med = float(Y.median())
    for label, C in (("raw", raw), ("meanmarg", mmcov)):
        L = torch.linalg.cholesky(C + 1e-8 * I)
        print(f"===== {label} posterior =====")
        print(f"{'tau':>7}{'a=0.50':>10}{'a=0.80':>10}{'a=0.95':>10}   (certified volume)")
        for tau in (0.5 * med, 0.75 * med, med, 1.25 * med):
            row = f"{tau:>7.3f}"
            with torch.no_grad():
                draws = (mean + L @ z).T
                for a in (0.5, 0.8, 0.95):
                    ce = conservative_estimate(draws, tau, a)
                    row += f"{float(ce.double().mean()):>10.4f}"
            k = certified_topk(draws, med, 0.95)
            print(row + f"   topk@median={len(k)}")
        print()


if __name__ == "__main__":
    main()
