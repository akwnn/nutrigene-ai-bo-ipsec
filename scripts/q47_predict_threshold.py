"""Q47 — the REGISTERED PREDICTION, as a computation rather than a hunch.

    python scripts/q47_predict_threshold.py     # log at results/q47-prediction.log

Run and committed **before** `run_q47_multifidelity.py` exists. Its output is the
prediction the real experiment is scored against.

THE PROXY MODEL
---------------
Strip the landscape out and keep only the order statistics. `N` candidate points carry
iid standard-normal true values `y`. A readout with correlation `c` to the truth is
`c*y + sqrt(1-c^2)*e`. Two readouts:

    cheap       corr = rho          (the swept parameter)
    expensive   corr = rho_e        (MEASURED on this project's own ensemble, below)

Scoring is this project's rule A, `diagnostics.reported_best_curve`: **pick the point by
the observation, score it by the truth.** So the confirmation step is not free — a noisy
expensive readout can fail to identify the best of the points it confirmed.

    single tier   48 expensive points, report the argmax of their observations
    two tier      n_cheap cheap points -> top k by cheap value -> k expensive
                  confirmations -> report the argmax of those k observations

WHAT IT IGNORES, AND WHY THAT IS THE POINT
------------------------------------------
No landscape, no GP, no spatial structure, no design. It therefore predicts **rule A
only**, and the registered prediction says out loud that rule C should behave
differently for a reason this model cannot see: the top-k design is clustered in the
high-response region, which is a poor design for fitting a surface.

`rho_e` is not assumed. It is the correlation between this project's own observation
model `y = f(x)(1+eps) + eta` and `f`, measured over 4096 Sobol points on all 25
instances at each cell:

    d=6  sigma_rel=0.25 -> 0.583      d=6  sigma_rel=0.10 -> 0.872
    d=8  sigma_rel=0.25 -> 0.557      d=8  sigma_rel=0.10 -> 0.863

**That measurement is itself a finding and it reframes the brief.** A cheap readout with
rho above rho_e is not a lower-fidelity anything — it is a *more accurate assay that also
costs less*, and the honest recommendation there is to stop running the expensive one.
At sigma_rel=0.25 that is true of everything above 0.583, which is half the swept range.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

RHO_E = {0.25: 0.583, 0.10: 0.872}          # measured; see docstring
BUDGET, PHI = 48, 1.0 / 3.0                  # cheap tier gets a third of the budget
RHOS = (0.30, 0.45, 0.55, 0.65, 0.80, 0.95)
COST_RATIOS = (3, 5, 10, 20)
M = 200_000
RULE = "=" * 92


def reported(y: np.ndarray, o: np.ndarray) -> np.ndarray:
    """rule A: argmax of the observation, scored by the truth."""
    return y[np.arange(y.shape[0]), np.argmax(o, axis=1)]


def main() -> None:
    rng = np.random.default_rng(0)
    k = int(round((1.0 - PHI) * BUDGET))
    print(f"{RULE}\nQ47 REGISTERED PREDICTION — Gaussian order-statistic proxy, rule A "
          f"only\n{RULE}")
    print(f"  budget {BUDGET} expensive-equivalents, cheap tier gets phi={PHI:.4f} "
          f"of it -> k={k} confirmations\n")
    for sigma, rho_e in RHO_E.items():
        y = rng.standard_normal((M, BUDGET))
        o = rho_e * y + np.sqrt(1 - rho_e**2) * rng.standard_normal(y.shape)
        base = float(reported(y, o).mean())
        print(f"  sigma_rel={sigma}   corr(expensive obs, truth)={rho_e}   "
              f"single-tier E[y reported] = {base:+.4f}")
        print(f"    {'cost':>5} {'n_cheap':>8}   " +
              "  ".join(f"rho={r:.2f}" for r in RHOS))
        for c in COST_RATIOS:
            n_cheap = int(round(PHI * BUDGET * c))
            gains = []
            for rho in RHOS:
                yy = rng.standard_normal((M // 4, n_cheap))
                u = rho * yy + np.sqrt(1 - rho**2) * rng.standard_normal(yy.shape)
                sel = np.argsort(-u, axis=1)[:, :k]
                ys = np.take_along_axis(yy, sel, axis=1)
                os_ = rho_e * ys + np.sqrt(1 - rho_e**2) * rng.standard_normal(ys.shape)
                gains.append(float(reported(ys, os_).mean()) - base)
            print(f"    {c:>4}x {n_cheap:>8}   " +
                  "  ".join(f"{g:>+8.3f}" for g in gains))
        print()
    print(f"{RULE}\n  Positive = the two-tier design reports a better point at equal "
          f"total cost.\n{RULE}")


if __name__ == "__main__":
    sys.exit(main())
