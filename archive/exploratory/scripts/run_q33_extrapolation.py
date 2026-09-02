"""Q33 — extrapolation geometry on the published Hall/Ogle stage-2 data.

    PYTHONPATH=src OMP_NUM_THREADS=1 python scripts/run_q33_extrapolation.py

**Registered in `docs/OPEN-QUESTIONS.md` Q33 before this ran, gate included.** One
measurement: fit a second-order polynomial and a GP to the same published conditions,
locate each model's argmax, read off the coordinates. The design region is coded
`[-1, +1]`, so a coordinate outside it means the model extrapolated.

**Geometry, not outcome.** No ground-truth surface is needed and none exists. Nothing
here says what would have happened at either recommendation; the only outcome evidence
is the published record of what happened at the polynomial's.

**One locator for both arms.** `metrics.constrained_argmax`, identical restarts,
raw_samples and seed. `tests/test_q33_extrapolation.py` asserts it rather than trusting
a reading of this file: two optimizers at different screening budgets is a defect this
project has already logged once.

Deviation from the brief, declared: LOO is an explicit per-fold refit loop rather than
`batch_cross_validation`. That helper validates a **default** `SingleTaskGP` — bare RBF,
no Matern, no `ScaleKernel`, no `Normalize` — unless `model_init_kwargs` is threaded
through, and `Standardize(m=m)` raises without `batch_shape=torch.Size([n])`. Both are
recorded blockers in the build plan. At n=24 an explicit loop refits `build_gp` in its
production configuration, which is the thing the check is supposed to be about.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.metrics import constrained_argmax          # noqa: E402
from boec.rsm import fit_second_order, second_order_design_matrix  # noqa: E402
from boec.surrogate import build_gp                  # noqa: E402

FACTORS = ["c", "civ", "ln411", "fn"]
EXTENSION = 2.0          # double the design half-width; contains TheO's coded +1.40
N_RESTARTS = 20          # IDENTICAL for both arms
RAW_SAMPLES = 4096       # IDENTICAL for both arms
SEED = 0                 # IDENTICAL for both arms

#: TheO, the published optimum, in stage-2 coded space. C 35.6 of [0, 71]; CIV 67.2 of
#: [0, 56] (the Results reading, settled in pdf_crosscheck.md:56); LN411 0.9 of [0, 1.6];
#: FN 22 of [22, 75]. Fibronectin at exactly -1 is the design floor, not an optimum.
THEO = np.array([0.0028, 1.4000, 0.1250, -1.0000])

RULE = "=" * 86


def load_stage2():
    """Load the canonical CSV and halt on any fidelity mismatch."""
    rows = list(csv.DictReader((ROOT / "data/published/hall_ogle_2025_stage2.csv").open()))
    if len(rows) != 25:
        raise AssertionError(f"expected 25 conditions, got {len(rows)}")
    X = np.array([[int(r[f]) for f in FACTORS] for r in rows], dtype=float)
    bad = sorted({v for v in X.ravel()} - {-1.0, 0.0, 1.0})
    if bad:
        raise AssertionError(f"coded levels outside {{-1,0,+1}}: {bad}")
    y = np.array([float(r["response"]) if r["response"] else np.nan for r in rows])
    sd = np.array([float(r["response_sd"]) if r["response_sd"] else np.nan for r in rows])
    ids = np.array([int(r["run_id"]) for r in rows])
    ok = np.where(~np.isnan(y))[0]
    M = second_order_design_matrix(X[ok])
    rank = int(np.linalg.matrix_rank(M))
    if (M.shape[1], rank) != (15, 15):
        raise AssertionError(
            f"second-order model matrix is {M.shape[1]} terms at rank {rank}; the "
            "quadratic is not estimable on the usable conditions")
    return X, y, sd, ids, ok


def leverage(model, x: np.ndarray) -> float:
    """h = x0' (X'X)^-1 x0 for the polynomial's design, at a point in coded space."""
    m = second_order_design_matrix(x.reshape(1, -1))[0]
    return float(m @ model.XtX_inv @ m)


def loo(X: np.ndarray, y: np.ndarray, sd: np.ndarray, bounds) -> dict:
    """Leave-one-out with a genuine refit per fold, for both model classes."""
    poly_err, gp_err = [], []
    for i in range(len(X)):
        keep = np.setdiff1d(np.arange(len(X)), [i])
        pm = fit_second_order(torch.tensor(X[keep]), torch.tensor(y[keep].reshape(-1, 1)))
        poly_err.append(float(pm.predict(torch.tensor(X[[i]])).item()) - y[i])
        g = build_gp(torch.tensor(X[keep]), torch.tensor(y[keep].reshape(-1, 1)),
                     torch.tensor((sd[keep] ** 2).reshape(-1, 1)), bounds)
        with torch.no_grad():
            mu = g.posterior(torch.tensor(X[[i]])).mean.item()
        gp_err.append(mu - y[i])
    p, g = np.array(poly_err), np.array(gp_err)
    return {"poly_rmse": float(np.sqrt((p ** 2).mean())),
            "gp_rmse": float(np.sqrt((g ** 2).mean())),
            "poly_mae": float(np.abs(p).mean()), "gp_mae": float(np.abs(g).mean())}


def main() -> None:
    X, y, sd, ids, ok = load_stage2()
    d = len(FACTORS)
    design_box = torch.stack([torch.full((d,), -1.0, dtype=torch.double),
                              torch.full((d,), 1.0, dtype=torch.double)])
    search_box = torch.stack([torch.full((d,), -EXTENSION, dtype=torch.double),
                              torch.full((d,), EXTENSION, dtype=torch.double)])

    print(f"\n{RULE}\nQ33 — EXTRAPOLATION GEOMETRY, published Hall/Ogle stage 2")
    print(f"{len(ok)} usable of {len(y)} conditions · coded space · search box "
          f"[-{EXTENSION}, +{EXTENSION}]^{d}")
    print(f"one locator for both arms: constrained_argmax(n_restarts={N_RESTARTS}, "
          f"raw_samples={RAW_SAMPLES}, seed={SEED})\n{RULE}")

    Xo, yo, sdo = X[ok], y[ok], sd[ok]
    poly = fit_second_order(torch.tensor(Xo), torch.tensor(yo.reshape(-1, 1)))
    gp = build_gp(torch.tensor(Xo), torch.tensor(yo.reshape(-1, 1)),
                  torch.tensor((sdo ** 2).reshape(-1, 1)), design_box)

    def poly_predict(Z):
        return poly.predict(Z)

    def gp_predict(Z):
        with torch.no_grad():
            return gp.posterior(Z).mean

    xp, vp, _ = constrained_argmax(poly_predict, search_box, n_restarts=N_RESTARTS,
                                   raw_samples=RAW_SAMPLES, seed=SEED)
    xg, vg, _ = constrained_argmax(gp_predict, search_box, n_restarts=N_RESTARTS,
                                   raw_samples=RAW_SAMPLES, seed=SEED)
    xp_np, xg_np = xp.numpy().ravel(), xg.numpy().ravel()
    out_p = np.maximum(np.abs(xp_np) - 1.0, 0.0)
    out_g = np.maximum(np.abs(xg_np) - 1.0, 0.0)

    print("\n[1] ARGMAX, per coordinate (coded)\n")
    print(f"  {'':<12}" + "".join(f"{f:>12}" for f in FACTORS))
    print(f"  {'polynomial':<12}" + "".join(f"{v:>12.4f}" for v in xp_np))
    print(f"  {'GP':<12}" + "".join(f"{v:>12.4f}" for v in xg_np))
    print(f"  {'TheO':<12}" + "".join(f"{v:>12.4f}" for v in THEO))

    print("\n[2] DISTANCE BEYOND +/-1, per coordinate\n")
    print(f"  {'':<12}" + "".join(f"{f:>12}" for f in FACTORS) + f"{'max':>10}{'total':>10}")
    print(f"  {'polynomial':<12}" + "".join(f"{v:>12.4f}" for v in out_p)
          + f"{out_p.max():>10.4f}{out_p.sum():>10.4f}")
    print(f"  {'GP':<12}" + "".join(f"{v:>12.4f}" for v in out_g)
          + f"{out_g.max():>10.4f}{out_g.sum():>10.4f}")
    for nm, v, o in (("polynomial", xp_np, out_p), ("GP", xg_np, out_g)):
        at_wall = [FACTORS[i] for i in range(d) if abs(abs(v[i]) - EXTENSION) < 1e-6]
        on_floor = [FACTORS[i] for i in range(d) if abs(v[i] + 1.0) < 1e-6]
        print(f"    {nm}: at the SEARCH-BOX wall in {at_wall or 'none'}; "
              f"on the design boundary in {on_floor or 'none'}")

    print("\n[3] LEVERAGE h at each recommendation "
          f"(polynomial design, p={poly.p}, n={poly.n}, residual df={poly.residual_df})\n")
    for nm, v in (("polynomial", xp_np), ("GP", xg_np), ("TheO", THEO)):
        print(f"  {nm:<12} h = {leverage(poly, v):>12.3f}")
    print(f"  {'(mean over the 24 design points)':<12} "
          f"h = {np.mean([leverage(poly, xi) for xi in Xo]):>7.3f}")

    print("\n[4] PREDICTION AND INTERVAL at each model's OWN recommendation\n")
    lo_p, hi_p = poly.prediction_interval(torch.tensor(xp_np.reshape(1, -1)))[1:]
    print(f"  polynomial at its argmax: {vp:>8.3f}  "
          f"95% PI [{float(lo_p):.3f}, {float(hi_p):.3f}]  "
          f"half-width {float(hi_p - lo_p) / 2:.3f}")
    with torch.no_grad():
        post = gp.posterior(torch.tensor(xg_np.reshape(1, -1)))
        gsd = float(post.variance.sqrt().item())
    print(f"  GP at its argmax:         {vg:>8.3f}  "
          f"95% latent [{vg - 1.96 * gsd:.3f}, {vg + 1.96 * gsd:.3f}]  "
          f"half-width {1.96 * gsd:.3f}")
    print(f"  observed best of the 24 usable conditions: {yo.max():.3f} "
          f"(run {ids[ok][int(yo.argmax())]})")

    print("\n[5] DISTANCE BETWEEN THE TWO RECOMMENDATIONS\n")
    print(f"  euclidean {np.linalg.norm(xp_np - xg_np):.4f}   per coordinate "
          f"{np.round(xp_np - xg_np, 4).tolist()}")

    print("\n[6] AGAINST TheO, the published optimum\n")
    print(f"  polynomial - TheO: euclidean {np.linalg.norm(xp_np - THEO):.4f}   "
          f"per coordinate {np.round(xp_np - THEO, 4).tolist()}")
    print(f"  GP         - TheO: euclidean {np.linalg.norm(xg_np - THEO):.4f}   "
          f"per coordinate {np.round(xg_np - THEO, 4).tolist()}")
    print(f"  TheO itself is outside the design region by "
          f"{np.maximum(np.abs(THEO) - 1, 0).max():.4f} (Collagen IV, coded +1.40)")

    print("\n[7] THE POLYNOMIAL'S UNCONSTRAINED STATIONARY POINT\n")
    sp = poly.stationary_point(design_box)
    print(f"  kind: {sp.kind}   inside the design region: {sp.inside_box}")
    print(f"  x = {None if sp.x is None else np.round(sp.x.numpy().ravel(), 4).tolist()}")
    print(f"  Hessian eigenvalues (ascending): "
          f"{np.round(sp.eigenvalues.numpy().ravel(), 4).tolist()}")
    if sp.x is not None:
        sv = sp.x.numpy().ravel()
        print(f"  beyond +/-1 per coordinate: "
              f"{np.round(np.maximum(np.abs(sv) - 1, 0), 4).tolist()}")

    print("\n[8] LEAVE-ONE-OUT, per-fold refit — the check on the whole exercise\n")
    m = loo(Xo, yo, sdo, design_box)
    print(f"  {'model':<12}{'LOO RMSE':>12}{'LOO MAE':>12}")
    print(f"  {'polynomial':<12}{m['poly_rmse']:>12.4f}{m['poly_mae']:>12.4f}")
    print(f"  {'GP':<12}{m['gp_rmse']:>12.4f}{m['gp_mae']:>12.4f}")
    print(f"  sd of the 24 responses: {yo.std(ddof=1):.4f}  "
          f"(a model no better than this predicts nothing)")
    better = "GP" if m["gp_rmse"] < m["poly_rmse"] else "polynomial"
    print(f"  -> {better} fits these conditions better by RMSE. If the two are close, "
          f"the recommendation\n     comparison below means correspondingly less.")

    print(f"\n[9] THE REGISTERED PREDICTION\n")
    poly_out = out_p.max() > 1e-6
    gp_out = out_g.max() > 1e-6
    print(f"  polynomial's argmax outside the design region: {poly_out} "
          f"(max {out_p.max():.4f})")
    print(f"  GP's argmax outside:                           {gp_out} "
          f"(max {out_g.max():.4f})")
    if poly_out and not gp_out:
        verdict = ("HELD in full — the polynomial extrapolated where the GP did not. "
                   "The mechanism reproduces on real data.")
    elif poly_out and out_g.max() < out_p.max():
        verdict = ("PARTIAL — both extrapolated, the GP materially less. Report both "
                   "distances; the difference is the finding.")
    elif poly_out:
        verdict = ("REFUTED — the GP extrapolated as far or further. The Phase 1 "
                   "mechanism does NOT transfer; it is about the synthetic landscape, "
                   "not the model classes. Report this at least as prominently.")
    else:
        verdict = ("REFUTED — the polynomial's argmax is inside the design region. "
                   "The primary claim fails at its first clause.")
    print(f"\n  {verdict}")
    print(f"\n{RULE}\n  Registered in Q33, gate included, before this ran. "
          f"Reported as it came out.\n{RULE}")


if __name__ == "__main__":
    main()
