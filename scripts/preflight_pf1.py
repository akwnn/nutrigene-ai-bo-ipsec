"""PF1 — the over-prediction surface over the registered (kappa, rho) grid.

OWNERSHIP: Person A. Reproduce with `python scripts/preflight_pf1.py`.

**This implements OPEN-QUESTIONS Q16, which was committed before this script ran.**
The result is the *grid*, not a cell. The registered primary is a directional trend:

    over-prediction increases monotonically with rho, and decreases with kappa

tested per instance and aggregated with an **instance-level cluster bootstrap**. Four
kappa on one landscape are four measurements of one landscape, not four independent
observations -- B fixed that nested-clustering bug once already in 0fc2610 and it
applies here identically.

Secondary: over-prediction decreases with the instance's true depth.

Falsifiable, and that matters: a non-monotone trend, or a bootstrap interval covering
zero, fails the claim. The four unit-cube numbers we already had do not establish it.

Why a trend rather than a corner. The endpoint moved four times -- unit cube, then
rho=1.2, then 2.0, then 3.0 -- each move after seeing a result. A trend survives the
next oracle change and transfers to Phases 2 and 3; a corner does neither, and the
oracle has already changed once (v6 -> v8).

Uses B's shared functions throughout: `designs.central_composite`,
`designs.sub_box_bounds`, `designs.extended_box_bounds`, `rsm.fit_second_order`,
`metrics.over_prediction_at_constrained_argmax`. Supersedes the archived pre-merge
`preflight.py`, whose sweep this reimplements against B's API.

Efficiency note, because it changes what is feasible: the training data depends only
on (instance, kappa), NOT on rho. So the surface is fit **once per (instance, kappa)**
and reused across all five rho -- 160 fits instead of 800.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr

from boec.designs import central_composite, extended_box_bounds, scale_to_box, sub_box_bounds
from boec.metrics import over_prediction_at_constrained_argmax
from boec.oracles import load_ensemble
from boec.rsm import fit_second_order
from boec.torch_oracle import BiphasicOracle

# --- REGISTERED GRID (OPEN-QUESTIONS Q16). Do not edit after seeing results. ---
KAPPAS = (0.6, 0.7, 0.8, 0.9)
RHOS = (1.2, 1.5, 2.0, 3.0, float("inf"))
DIM = 6
SIGMA_REL = 0.10
N_BOOT = 2000
N_RESTARTS = 20
RAW_SAMPLES = 4096
KINDS = ("maximum", "minimum", "saddle", "ridge")


def rho_label(r: float) -> str:
    return "cube" if r == float("inf") else f"{r:g}"


def run(n_instances: int | None = None) -> list[dict]:
    """One row per (instance, kappa, rho)."""
    ens = load_ensemble(dim=DIM)
    if n_instances:
        ens = ens[:n_instances]
    design = central_composite(DIM, n_centre=4, n_derived=1, face_centred=True)
    rows: list[dict] = []

    for k, inst in enumerate(ens):
        orc = BiphasicOracle(inst, sigma_rel=SIGMA_REL, seed=k)
        for kappa in KAPPAS:
            sub = sub_box_bounds(orc.x_star, kappa)
            train_X = scale_to_box(design.coded, sub)
            train_Y, _ = orc.observe(train_X)
            fit = fit_second_order(train_X, train_Y)          # once per (instance, kappa)
            kind = fit.stationary_point(sub).kind

            for rho in RHOS:
                box = extended_box_bounds(orc.x_star, kappa, rho)
                res = over_prediction_at_constrained_argmax(
                    fit.predict, orc.truth, box,
                    n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES, seed=k,
                )
                rows.append(dict(
                    instance=inst.instance_id, depth=float(inst.true_depth),
                    kappa=kappa, rho=rho, kind=kind,
                    over=float(res.over_prediction),
                    pi=float(fit.prediction_interval_width(res.x_argmax.unsqueeze(0))),
                    escaped=bool(not (
                        torch.all(res.x_argmax >= sub[0] - 1e-12)
                        and torch.all(res.x_argmax <= sub[1] + 1e-12)
                    )),
                ))
    return rows


def _cluster_boot(per_instance: np.ndarray, seed: int = 0) -> tuple[float, float, float]:
    """Mean and 95% CI, resampling INSTANCES with replacement -- never cells."""
    rng = np.random.default_rng(seed)
    n = len(per_instance)
    draws = np.array([per_instance[rng.integers(0, n, n)].mean() for _ in range(N_BOOT)])
    return float(per_instance.mean()), float(np.percentile(draws, 2.5)), float(
        np.percentile(draws, 97.5))


def report(rows: list[dict]) -> dict:
    inst_ids = sorted({r["instance"] for r in rows})
    print(f"\n{'=' * 92}")
    print(f"PF1 · REGISTERED (kappa x rho) GRID · d={DIM} · {len(inst_ids)} instances "
          f"· sigma_rel={SIGMA_REL}")
    print(f"{'=' * 92}")

    # --- the surface -----------------------------------------------------
    print(f"\nMedian over-prediction (response max is 1.0)\n")
    print(f"{'kappa':>7} " + "".join(f"{'rho ' + rho_label(r):>12}" for r in RHOS))
    for kappa in KAPPAS:
        cells = []
        for rho in RHOS:
            v = [r["over"] for r in rows if r["kappa"] == kappa and r["rho"] == rho]
            cells.append(f"{np.median(v):>12.3f}")
        print(f"{kappa:>7} " + "".join(cells))

    print(f"\nMedian second-order PI width at the argmax\n")
    print(f"{'kappa':>7} " + "".join(f"{'rho ' + rho_label(r):>12}" for r in RHOS))
    for kappa in KAPPAS:
        cells = []
        for rho in RHOS:
            v = [r["pi"] for r in rows if r["kappa"] == kappa and r["rho"] == rho]
            cells.append(f"{np.median(v):>12.3f}")
        print(f"{kappa:>7} " + "".join(cells))

    # --- registered primary: monotone trends, instance-level -------------
    print(f"\n{'=' * 92}\nREGISTERED PRIMARY — monotone trend, per instance, "
          f"instance-level cluster bootstrap\n{'=' * 92}")
    finite = [r for r in RHOS if np.isfinite(r)]
    rho_rhos, kap_rhos = [], []
    for iid in inst_ids:
        sub = [r for r in rows if r["instance"] == iid]
        for kappa in KAPPAS:                       # trend in rho, within each kappa
            v = [(r["rho"], r["over"]) for r in sub
                 if r["kappa"] == kappa and np.isfinite(r["rho"])]
            if len(v) > 2:
                rho_rhos.append(spearmanr([a for a, _ in v], [b for _, b in v]).statistic)
        for rho in finite:                          # trend in kappa, within each rho
            v = [(r["kappa"], r["over"]) for r in sub if r["rho"] == rho]
            if len(v) > 2:
                kap_rhos.append(spearmanr([a for a, _ in v], [b for _, b in v]).statistic)

    # Aggregate to ONE value per instance before bootstrapping.
    per_inst_rho = np.array([
        np.mean([spearmanr(
            [r["rho"] for r in rows if r["instance"] == iid and r["kappa"] == k
             and np.isfinite(r["rho"])],
            [r["over"] for r in rows if r["instance"] == iid and r["kappa"] == k
             and np.isfinite(r["rho"])]).statistic for k in KAPPAS])
        for iid in inst_ids])
    per_inst_kap = np.array([
        np.mean([spearmanr(
            [r["kappa"] for r in rows if r["instance"] == iid and r["rho"] == p],
            [r["over"] for r in rows if r["instance"] == iid and r["rho"] == p]).statistic
            for p in finite])
        for iid in inst_ids])

    m1, l1, u1 = _cluster_boot(per_inst_rho)
    m2, l2, u2 = _cluster_boot(per_inst_kap)
    print(f"  trend in rho   (expect POSITIVE): {m1:+.4f}  [{l1:+.4f}, {u1:+.4f}]"
          f"   -> {'HOLDS' if l1 > 0 else 'FAILS'}")
    print(f"  trend in kappa (expect NEGATIVE): {m2:+.4f}  [{l2:+.4f}, {u2:+.4f}]"
          f"   -> {'HOLDS' if u2 < 0 else 'FAILS'}")

    # --- registered secondary: depth -------------------------------------
    print(f"\n{'=' * 92}\nREGISTERED SECONDARY — over-prediction vs instance true depth"
          f"\n{'=' * 92}")
    depths = np.array([[r for r in rows if r["instance"] == i][0]["depth"] for i in inst_ids])
    for kappa in (0.6, 0.9):
        vals = np.array([np.median([r["over"] for r in rows
                                    if r["instance"] == i and r["kappa"] == kappa])
                         for i in inst_ids])
        rho_s = spearmanr(depths, vals).statistic
        print(f"  kappa={kappa}: Spearman(true_depth, over-prediction) = {rho_s:+.4f}"
              f"   (expect NEGATIVE)")
    print(f"  depth range across instances: [{depths.min():.4f}, {depths.max():.4f}]"
          f"  -- narrow depth range limits this test's power")

    # --- descriptive ------------------------------------------------------
    kinds = {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS}
    esc = np.mean([r["escaped"] for r in rows])
    print(f"\n  turning points across all cells: {kinds}")
    print(f"  argmax escaped the training sub-box: {esc:.0%} of cells")
    return dict(trend_rho=[m1, l1, u1], trend_kappa=[m2, l2, u2], kinds=kinds)


if __name__ == "__main__":
    rows = run()
    summary = report(rows)
    out = Path("results/pf1-grid.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"grid": rows, "summary": summary}, indent=1, default=str))
    print(f"\nwritten to {out}")
