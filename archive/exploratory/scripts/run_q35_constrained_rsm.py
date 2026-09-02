"""Q35 / T1.2 — the constrained-RSM arm: score the DoE surface the way practice says to.

    python scripts/run_q35_constrained_rsm.py                 # primary cell
    python scripts/run_q35_constrained_rsm.py --all-cells

**NO NEW CAMPAIGNS.** This is a third scoring of the DoE runs E2 already made. No E2
number moves and `e2.yaml`'s registered rule is untouched.

THE OBJECTION THIS ANSWERS
--------------------------
Classical response-surface practice does not read a quadratic's optimum off an
unbounded search. Box & Draper warn against exactly that, and the standard remedy is
**ridge analysis** -- constrain the predicted optimum to the region actually explored.
The DoE arm as run searches the kept factors' full range (`doe.py:334`, deliberately:
"whether that lands outside the region they explored is the finding"). A reviewer reads
that as the safeguard being switched off, and they are entitled to.

So all THREE scorings are computed and all three are reported:

    best observed          what a practitioner walks away with
    UNCONSTRAINED argmax   what the source paper did -- JMP's Solution report, the
                           unconstrained stationary point. Verified: the words
                           "profiler", "desirability", "maximize", "stationary point"
                           and "canonical analysis" appear ZERO times in that paper,
                           while "prediction solution" appears.
    CONSTRAINED argmax     what competent practice prescribes -- maximize over the
                           stage-2 design region only

**Registered before the run, because the outcome is loaded:** if the constrained
recommendation is much better, the published failure is a PRACTICE failure rather than
a METHOD failure, and the claim narrows to "unconstrained polynomial surfaces
extrapolate badly, and the source study used the unconstrained form." That is a
legitimate result and it is reported either way. Reporting only the unconstrained
version is a strawman; reporting only the constrained version abandons the case study.

RIDGE ANALYSIS IS CLOSED-FORM HERE, SO NO OPTIMIZER IS USED
-----------------------------------------------------------
For `f(x) = b0 + b'x + x'Bx` with Hessian `H`, the maximum on the sphere
`||x - x0|| = r` satisfies `grad f = nu (x - x0)`, i.e. with `u = x - x0` and
`g0 = grad f(x0) = b + H x0`:

    u(nu) = (nu I - H)^{-1} g0,        r(nu) = ||u(nu)||

`nu > lambda_max(H)` makes `(nu I - H)` positive definite and picks out the MAXIMUM on
that sphere rather than another stationary point. Sweeping `nu` down toward
`lambda_max` traces the ridge path outward from the centroid. This is Box & Draper's
construction, not a numerical search, so there is no optimizer seed to argue about.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import warnings

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scipy.stats import wilcoxon                                      # noqa: E402

from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.metrics import constrained_argmax                           # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.rsm import classify_stationary_point, fit_second_order      # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402

BUDGET = 48
N_INSTANCES = 25
N_SEEDS = 2
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
N_RESTARTS = 20
RAW_SAMPLES = 4096
#: Fidelity: the refitted surface must reproduce the arm's own predicted optimum.
REFIT_TOL = 1e-6
RULE = "=" * 96


def _hessian(beta: np.ndarray, d: int) -> np.ndarray:
    """`H[i,i] = 2 c_i`, `H[i,j] = e_ij` — the same construction as `rsm`."""
    c = beta[1 + d: 1 + 2 * d]
    H = np.zeros((d, d))
    np.fill_diagonal(H, 2.0 * c)
    k = 1 + 2 * d
    for i in range(d):
        for j in range(i + 1, d):
            H[i, j] = H[j, i] = beta[k]
            k += 1
    return H


def ridge_path(beta: np.ndarray, d: int, x0: np.ndarray, region: np.ndarray,
               n_steps: int = 400) -> dict:
    """Box & Draper ridge analysis: the max of the surface on spheres about `x0`.

    Returns the radius at which the path leaves `region`, and the region's own
    circumradius from `x0` for scale. Closed form -- see the module docstring.
    """
    b = beta[1: 1 + d]
    H = _hessian(beta, d)
    g0 = b + H @ x0
    lam_max = float(np.linalg.eigvalsh(H).max())

    # nu sweeps down toward lambda_max, so r sweeps outward from 0
    scale = max(abs(lam_max), np.linalg.norm(H, 2), 1.0)
    nus = lam_max + scale * np.logspace(2, -6, n_steps)
    lo, hi = region[0], region[1]
    corner_r = float(np.linalg.norm(np.maximum(hi - x0, x0 - lo)))

    path, exit_r = [], None
    for nu in nus:
        try:
            u = np.linalg.solve(nu * np.eye(d) - H, g0)
        except np.linalg.LinAlgError:
            continue
        x = x0 + u
        r = float(np.linalg.norm(u))
        inside = bool(np.all(x >= lo - 1e-9) and np.all(x <= hi + 1e-9))
        yhat = float(beta[0] + b @ x + x @ H @ x / 2.0)
        path.append(dict(nu=float(nu), r=r, yhat=yhat, inside=inside))
        if exit_r is None and not inside:
            exit_r = r
    return dict(exit_radius=exit_r, region_corner_radius=corner_r,
                lambda_max=lam_max, n_path=len(path),
                max_radius_reached=max((p["r"] for p in path), default=0.0))


def run_cell(dim: int, sigma: float) -> list[dict]:
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    rows: list[dict] = []
    for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
        for seed in range(N_SEEDS):
            o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            r = run_doe_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=seed)
            opt = float(inst.optimum_value)
            kept = list(r.kept_factors)
            k = len(kept)

            # Refit the arm's own stage-2 surface from the stored measurements.
            s2 = slice(r.n_stage1, r.n_stage1 + r.n_stage2)
            X2 = r.X_visited[s2][:, kept]
            Y2 = r.Y_visited[s2]
            fit = fit_second_order(X2, Y2)

            def lift(x_kept: torch.Tensor) -> torch.Tensor:
                full = torch.tensor([r.dropped_held_at.get(i, 0.0) for i in range(dim)],
                                    dtype=torch.double)
                full[kept] = x_kept.double().reshape(-1)
                return full.unsqueeze(0)

            # FIDELITY GATE — if the refit is not the arm's model, everything below
            # describes a different surface and the comparison is void.
            x_un, y_un, _ = constrained_argmax(fit.predict, r.search_bounds,
                                               n_restarts=N_RESTARTS,
                                               raw_samples=RAW_SAMPLES, seed=seed)
            drift = float(np.abs(y_un - r.predicted_y))
            if drift > REFIT_TOL:
                raise AssertionError(
                    f"refit does not reproduce the arm's predicted optimum: "
                    f"{y_un:.10f} vs {r.predicted_y:.10f} (|delta| {drift:.3e}) "
                    f"at instance={inst.instance_id} seed={seed}")

            # --- the three scorings -------------------------------------------
            # D20: rule A is the true value at the running OBSERVED argmax. Reading
            # `curve_true` here scored this column at oracle-best -- the running best
            # TRUE value among visited points -- which credits the arm for a recipe it
            # measured but could not identify, and is the error that voided E2 run 1.
            best_observed = opt - float(
                reported_best_curve(o.truth(r.X_visited), r.Y_visited)[-1])
            unconstrained = opt - float(o.truth(lift(x_un)))
            x_con, _, _ = constrained_argmax(fit.predict, r.stage2_bounds,
                                             n_restarts=N_RESTARTS,
                                             raw_samples=RAW_SAMPLES, seed=seed)
            constrained = opt - float(o.truth(lift(x_con)))

            # --- geometry ------------------------------------------------------
            sp = classify_stationary_point(fit.beta, k, bounds=r.stage2_bounds)
            centroid = r.stage2_bounds.numpy().mean(axis=0)
            ridge = ridge_path(fit.beta, k, centroid, r.stage2_bounds.numpy())

            rows.append(dict(
                instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                n_kept=k,
                best_observed=best_observed,
                unconstrained=unconstrained,
                constrained=constrained,
                over_prediction=float(r.over_prediction),
                confirmation_inside_stage2=bool(r.confirmation_inside_stage2),
                stationary_kind=sp.kind,
                stationary_inside_stage2=bool(sp.inside_box),
                eigenvalues=[float(v) for v in sp.eigenvalues],
                refit_drift=drift,
                **{f"ridge_{key}": val for key, val in ridge.items()},
            ))
    return rows


def _per_instance(rows, key) -> np.ndarray:
    return np.array([np.mean([r[key] for r in rows if r["instance"] == i])
                     for i in sorted({r["instance"] for r in rows})])


def _paired(rows, a, b) -> str:
    d = _per_instance(rows, a) - _per_instance(rows, b)
    m, lo, hi = instance_bootstrap(d, n_boot=2000)
    try:
        p = wilcoxon(d).pvalue
    except ValueError:
        p = float("nan")
    return f"{m:>+9.4f} [{lo:>+8.4f},{hi:>+8.4f}] p={p:<8.4f} n={len(d)}"


def report(rows, dim, sigma) -> None:
    tag = "   <-- PRIMARY CELL" if (dim, sigma) == (6, 0.25) else ""
    print(f"\n{RULE}\nQ35 · d={dim} · sigma={sigma} · {N_INSTANCES} instances x "
          f"{N_SEEDS} seeds{tag}\n{RULE}")
    print(f"{'DoE scoring':<44}{'mean regret':>13}{'median':>10}")
    for key, label in (("best_observed", "best observed  (E2's registered rule A)"),
                       ("unconstrained", "UNCONSTRAINED argmax  (what the paper did)"),
                       ("constrained", "CONSTRAINED argmax  (what practice says)")):
        v = _per_instance(rows, key)
        print(f"{label:<44}{v.mean():>13.4f}{np.median(v):>10.4f}")

    print(f"\n  {'contrast':<44}{'paired difference (>0 = first is worse)':>44}")
    print(f"  {'unconstrained - constrained':<44}{_paired(rows, 'unconstrained', 'constrained')}")
    print(f"  {'constrained - best observed':<44}{_paired(rows, 'constrained', 'best_observed')}")
    print(f"  {'unconstrained - best observed':<44}{_paired(rows, 'unconstrained', 'best_observed')}")

    n = len(rows)
    print(f"\n  stationary point of the fitted surface (n={n}):")
    for kind in ("maximum", "minimum", "saddle", "ridge"):
        c = sum(1 for r in rows if r["stationary_kind"] == kind)
        if c:
            inside = sum(1 for r in rows
                         if r["stationary_kind"] == kind and r["stationary_inside_stage2"])
            print(f"      {kind:<9} {c:>4} ({100 * c / n:>5.1f}%)   "
                  f"inside stage-2 region: {inside}")
    esc = sum(1 for r in rows if not r["confirmation_inside_stage2"])
    print(f"      predicted optimum fell OUTSIDE the stage-2 region: "
          f"{esc}/{n} ({100 * esc / n:.1f}%)")

    ex = [r["ridge_exit_radius"] for r in rows if r["ridge_exit_radius"] is not None]
    cr = [r["ridge_region_corner_radius"] for r in rows]
    if ex:
        print(f"\n  ridge path leaves the stage-2 region at radius: median "
              f"{np.median(ex):.4f}  (region corner radius median {np.median(cr):.4f})")
        print(f"      paths that never left the region: {len(rows) - len(ex)}/{n}")
    print(f"  max |refit drift| vs the arm's own predicted optimum: "
          f"{max(r['refit_drift'] for r in rows):.3e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-cells", action="store_true")
    args = ap.parse_args()

    everything, t0 = [], time.time()
    for dim, sigma in (CELLS if args.all_cells else [(6, 0.25)]):
        rows = run_cell(dim, sigma)
        everything.extend(rows)
        report(rows, dim, sigma)
        print(f"\n  [{time.time() - t0:.0f}s elapsed]", flush=True)

    out = ROOT / "results" / "q35-constrained-rsm.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(everything, indent=1))
    print(f"\n  written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
