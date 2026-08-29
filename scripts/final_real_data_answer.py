"""The fully-corrected SPADE, run on both real datasets. This is the product output.

Applies EVERY fix from this session at once, which nothing had done before:
  * `boec.meanmarg` -- the mean-uncertainty term whose omission collapsed the posterior
    297-484x on real data (`SPADE-PUBLISHED-ECM-RESULT.md` §2).
  * `c` LOO-calibrated ON EACH DATASET, never imported from simulation, which
    `SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10 showed does not transfer.
  * both estimands -- the region certificate and `boec.topk`'s finite set -- because the
    region one abstains far more often and the finite set may answer where it cannot.

PROVISIONAL: the in-house data is `awaiting_human_signoff`. Nothing here is a wet-lab
result.
"""
from __future__ import annotations

import sys, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

N_DRAWS = 4000


def frontier(mean, L, tau_lo, tau_hi, alpha, c, n_draws=N_DRAWS, seed=0):
    """Highest threshold certifiable over the WHOLE box, by bisection."""
    from boec.vorobev import conservative_estimate
    q = mean.shape[0]
    z = torch.randn(q, n_draws, generator=torch.Generator().manual_seed(seed),
                    dtype=torch.double)
    with torch.no_grad():
        draws = (mean + float(c) * L @ z).T
    lo, hi = tau_lo, tau_hi
    for _ in range(26):
        mid = (lo + hi) / 2
        if float(conservative_estimate(draws, mid, alpha).double().mean()) >= 0.999:
            lo = mid
        else:
            hi = mid
    return lo, draws


def run(label, X, Y, Yvar, c_star, tau_lo, tau_hi, unit):
    from boec.meanmarg import mean_marginalised_covariance
    from boec.surrogate import build_gp
    from boec.topk import certified_topk

    d = X.shape[1]
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    m = build_gp(X, Y, Yvar, bounds)
    cand = torch.rand(3000, d, generator=torch.Generator().manual_seed(0),
                      dtype=torch.double)
    with torch.no_grad():
        mean = m.posterior(cand).mean.reshape(-1, 1).double()
    cov = mean_marginalised_covariance(m, cand)
    cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
    L = torch.linalg.cholesky(cov)

    print(f"===== {label} =====")
    print(f"  n={X.shape[0]}  factors={d}  LOO-calibrated c = {c_star}")
    print(f"  {'confidence':>12}{'whole-region floor':>22}{'finite-set @ floor':>22}")
    for a in (0.50, 0.80, 0.95, 0.99):
        f_, draws = frontier(mean, L, tau_lo, tau_hi, a, c_star)
        k = certified_topk(draws, f_, a)
        got = f"{f_:.2f}{unit}" if f_ > tau_lo + 1e-3 else "nothing"
        print(f"  {a:>12.2f}{got:>22}{len(k):>22}")
    print()


def main():
    import importlib.util

    def _load(name, path):
        sp = importlib.util.spec_from_file_location(name, str(ROOT / path))
        mod = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mod)
        return mod

    # ---- in-house iPSC-EC coating assay -------------------------------------
    R = _load("R", "scripts/run_real_ipsc_certification.py")
    X, Y, Yvar = R.load()
    run("in-house iPSC-EC coating (CD31+ %)", X, Y, Yvar,
        c_star=0.712, tau_lo=10.0, tau_hi=50.0, unit="%")

    # ---- published Hall & Ogle 2025 ECM screen ------------------------------
    H = _load("H", "scripts/certify_hall_ogle.py")
    X2, Y2, Yvar2 = H.load()
    run("published Hall & Ogle 2025 ECM screen", X2, Y2, Yvar2,
        c_star=0.526, tau_lo=0.20, tau_hi=1.50, unit="")


if __name__ == "__main__":
    main()
