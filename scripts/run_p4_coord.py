"""P4 — `coord` at the primary cell, scored on the design-space deliverables.

    .venv/bin/python scripts/run_p4_coord.py --limit 2      # smoke
    .venv/bin/python scripts/run_p4_coord.py --gate-only    # regenerate and gate, write nothing
    .venv/bin/python scripts/run_p4_coord.py                # all 50

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) **before this file existed**.

WHAT IS MISSING, AND WHY IT IS THE CHEAPEST THING TO FIX
--------------------------------------------------------
`coord` — coordinate descent, Q3's "what a careful person does with no statistics
training" — has **50 gated campaigns** in `results/e2-grid.json` at d=6, sigma_rel=0.25
and **not one design-space metric anywhere**. K6 scored five arms, K6b scored the same
five, the spread runs added three more; `coord` was in none of them. Adding it widens
every design-space ranking in the project from 8 arms to 9 for one CPU-minute of
regeneration, because the campaign itself never fits a model.

It is also the arm most likely to embarrass the design-space framing, which is the
reason to run it rather than a reason not to: a one-factor-at-a-time sweep visits 48
points strung along six axis-aligned lines, so its posterior is well-informed on those
lines and nowhere else. Whether that reads as a good or a bad certified region is
exactly the question K6 exists to answer.

WHY THE REGENERATION LIVES HERE AND NOT IN `boec.replay`
---------------------------------------------------------
`coord` is not in `DETERMINISTIC_ARMS`, `OPTIMISED_ARMS`, `KERNEL_ARMS` or
`SPREAD_ARMS`, and `replay.py` is owned elsewhere this session. So the call is
reproduced here from `scripts/run_e2.py:113` — one fresh `BiphasicOracle`, one
`coordinate_descent(orc, bounds, budget=BUDGET, seed=seed)`, one `scored_curve` — and
`tests/test_p4_coord.py` gates the result against the committed `coord` column at
|delta| = 0 on all 50 rather than trusting that reproduction.

THE Yvar THE ARM THREW AWAY
---------------------------
`coordinate_descent` calls `evaluate` 48 times and keeps only ``Y``; the variance goes
in the bin. The GP needs it. **Re-evaluating is wrong** — it draws fresh noise, so it
returns a different `y` and a different plug-in variance from the one the campaign
carried (`boec.replay`'s module docstring records the same trap for the DoE arm). It is
recomputed instead from the **stored** ``Y`` with `_plug_in_yvar`, which for
`yvar_mode="plugin"` is bitwise the expression `BiphasicOracle.observe` evaluated;
`test_yvar_is_what_the_oracle_actually_returned` pins that by capturing the discarded
values as they go past.

THE SCORERS ARE THE COMMITTED SCORERS
--------------------------------------
`score_k6` **delegates** to `run_k6_designspace.score_campaign`, imported rather than
copied: a second copy of the 24-cell loop would be a second definition of every metric
in the table. K6b's loop lives inside its runner's `main()` and cannot be imported, so
it is reproduced here — but every metric in it comes from `boec.vorobev`, the draws come
from the committed `joint_draws`, and both scorers are gated in the tests against a
committed `lhs` row at **bitwise** equality before any `coord` number is read.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.baselines import coordinate_descent                        # noqa: E402
from boec.calibration import average_precision, error_volumes        # noqa: E402
from boec.designspace import (brier_and_auc, false_inclusion_rate,   # noqa: E402
                              gp_adapter, iou,
                              predictive_probability_map, probability_map)
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import (CampaignRecord, committed_rows,             # noqa: E402
                         instance_by_id, scored_curve, unit_bounds)
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar          # noqa: E402
from boec.vorobev import (alpha_star, conservative_estimate,         # noqa: E402
                          containment_probability, empirical_containment,
                          excursion_probability, vorobev_deviation,
                          vorobev_expectation)

ARM = "coord"
DIM, SIGMA, BUDGET = 6, 0.25, 48

#: K6's grid. Not a parameter — a different grid is a different metric.
GRID_N, GRID_SEED = 20_000, 0
#: K6b's constants, verbatim from `scripts/run_k6b_conservative.py`.
SUBSET_N, N_DRAWS = 2_000, 512
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
ALPHAS = (0.50, 0.80, 0.95)

E2_GRID = ROOT / "results" / "e2-grid.json"
OUT = ROOT / "results" / "p4-coord.json"

#: Exact. `coord` never calls an optimiser — every branch of `coordinate_descent` is a
#: comparison of floats already computed — so there is no L-BFGS-B path to excuse a
#: tolerance, and none is offered.
GATE_TOL = 0.0


def _import(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


#: Imported, never copied. `score_campaign` is the function that produced every committed
#: K6 row; `joint_draws` is the function that produced every committed K6b draw.
_K6 = _import("_run_k6_designspace", ROOT / "scripts" / "run_k6_designspace.py")
_K6B = _import("_run_k6b_conservative", ROOT / "scripts" / "run_k6b_conservative.py")


# ======================================================================================
# REGENERATION
# ======================================================================================

def regenerate_coord(instance: str, dim: int, sigma: float, seed: int) -> CampaignRecord:
    """Re-run one committed `coord` campaign. `run_e2.run_cell`'s three lines, verbatim.

    Returns a :class:`boec.replay.CampaignRecord` so every downstream scorer sees the
    same object it sees for every other arm. ``kept_factors``/``dropped_held_at`` are
    ``None``: coordinate descent sweeps **every** axis, so Amendment B3's subspace pin
    must not fire for it.
    """
    inst = instance_by_id(instance, dim)
    bounds = unit_bounds(dim)
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cd = coordinate_descent(orc, bounds, budget=BUDGET, seed=seed)
    X, Y = cd.X, cd.Y
    # From the STORED Y. Re-evaluating would draw fresh noise — see the module docstring.
    Yvar = torch.from_numpy(
        _plug_in_yvar(Y.detach().cpu().numpy(), orc.sigma_rel, orc.sigma_add))
    curve = scored_curve(orc, X, Y)
    return CampaignRecord(
        X=X, Y=Y, Yvar=Yvar, instance=instance, dim=dim, sigma=sigma, seed=seed,
        arm=ARM, regret=float(inst.optimum_value - curve[-1]),
        optimum_value=float(inst.optimum_value), kept_factors=None, dropped_held_at=None)


# ======================================================================================
# SCORING
# ======================================================================================

def auprc_pair(p: torch.Tensor, truth: torch.Tensor, tau: float) -> dict:
    """AUPRC on both classes, each with the baseline a no-skill ranker would score.

    **Amendment F2b.** Two things this does not do.

    It does not score the minority class as ``-truth >= -tau``. A point whose truth is
    exactly ``tau`` satisfies ``truth >= tau`` *and* ``-truth >= -tau``, so the negated
    form puts it in both classes; the explicit complement ``truth < tau`` is exclusive by
    construction. Ranking the complement means ranking by ``-p``.

    It does not report an AP without its baseline. A ranker with no skill scores the
    prevalence, not 0.5, and prevalence across this grid runs from 0.0012 to 0.999 -- so
    the positive-class AP is trivially near 1 at exactly the cells F2b flags as primary,
    where about 16 of 20,000 points are NEGATIVE. Both baselines travel on every row.
    """
    t = truth.reshape(-1)
    pos = t >= tau
    prevalence = float(pos.double().mean())
    ap = average_precision(p, truth, tau)
    # The complement, scored explicitly: label `truth < tau`, ranked by `-p`.
    #
    # `average_precision` labels `truth >= tau`, so the complement has to be expressed in
    # that form. Negating gives `-truth >= -tau`, which is `truth <= tau` -- it INCLUDES
    # the boundary, so a point at exactly `tau` lands in both classes, which is the whole
    # defect this function exists to avoid. `nextafter` moves the threshold to the
    # smallest float strictly above `-tau`, making the condition `-truth > -tau` exactly,
    # i.e. `truth < tau`, for every float64 input.
    comp_tau = float(np.nextafter(-float(tau), np.inf))
    ap_min = average_precision(-p.reshape(-1), -t, comp_tau)
    n_minority = int((t < tau).sum())
    assert n_minority == int((-t >= comp_tau).sum()), "complement label is not `truth < tau`"
    return {"auprc": float("nan") if ap is None else ap,
            "ap_baseline": prevalence,
            "auprc_minority": float("nan") if ap_min is None else ap_min,
            "ap_baseline_minority": 1.0 - prevalence,
            "n_positive": int(pos.sum()), "n_minority": n_minority}


def score_k6(rec: CampaignRecord, orc, grid: torch.Tensor,
             truth: torch.Tensor) -> list[dict]:
    """The 24 gamma x tau_frac cells, produced by K6's own `score_campaign`.

    Then enriched with Amendment F2a's error volumes and F2b's AUPRC. The volumes are
    pure arithmetic on columns K6 already returns. **AUPRC is not** -- it needs the
    `p_pred` vector, which `score_campaign` computes internally and discards, so P4
    rebuilds the maps.

    A second probability map is a second definition of every metric derived from it, so
    each row carries `_recomputed_*` copies of eight of K6's own columns, taken from
    P4's maps. `tests/test_p4_coord.py::test_the_auprc_maps_are_k6s_maps` requires them
    to match K6's row bitwise. That is what makes the AUPRC a column of the same table
    rather than a number from a lookalike.
    """
    active = torch.zeros(rec.dim, dtype=torch.bool)
    if rec.kept_factors is None:
        active[:] = True
    else:
        active[list(rec.kept_factors)] = True
    rows = _K6.score_campaign(rec, orc, grid, truth, active)

    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, X):
            return mean, sd

    m = _M()
    # A lab does not know f, so the predictive SD is a PLUG-IN from the posterior mean.
    # K6's line, reproduced because the map depends on it.
    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    for row in rows:
        tau, gamma = row["tau"], row["gamma"]
        p_pred = predictive_probability_map(m, grid, tau, sigma_pred)
        p_lat = probability_map(m, grid, tau)
        d_gamma = p_pred >= gamma
        latent = p_lat >= gamma
        prevalence = row["true_frac_above_tau"]

        for label, region, p in (("pred", d_gamma, p_pred), ("latent", latent, p_lat)):
            fi = false_inclusion_rate(region, truth, tau)
            ev = error_volumes(float(region.double().mean()), fi, prevalence)
            row[f"type_I_vol_{label}"] = ev["type_I_vol"]
            row[f"intersect_{label}"] = ev["intersect"]
            row[f"type_II_vol_{label}"] = ev["type_II_vol"]
            row[f"symmetric_difference_{label}"] = ev["total_error_vol"]
            row.update({f"{k}_{label}": v for k, v in auprc_pair(p, truth, tau).items()})
            # The self-gate: K6's own columns, recomputed from P4's maps.
            b, a = brier_and_auc(p, truth, tau)
            row[f"_recomputed_vol_{label}"] = float(region.double().mean())
            row[f"_recomputed_brier_{label}"] = b
            row[f"_recomputed_auc_{label}"] = a
            if label == "pred":
                row["_recomputed_iou_pred"] = iou(region, truth, tau)
                row["_recomputed_fi_pred"] = fi

    del model, mean, sd
    gc.collect()
    return rows


def score_k6b(rec: CampaignRecord, orc, X_sub: torch.Tensor,
              mu_max: float) -> list[dict]:
    """The conservative-excursion rows. `run_k6b_conservative.main`'s inner loop.

    Reproduced rather than imported because K6b's loop is inline in its `main()` and
    that function also owns argument parsing and file writing. Every *metric* is the
    library's; the draws are K6b's own `joint_draws`; and the whole thing is gated
    bitwise against a committed `lhs` row in `tests/test_p4_coord.py`.
    """
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))

    if rec.kept_factors is not None and rec.dropped_held_at:
        X_eval = X_sub.clone()
        for j, v in rec.dropped_held_at.items():
            X_eval[:, j] = v
    else:
        X_eval = X_sub
    with torch.no_grad():
        truth_eval = orc.truth(X_eval).reshape(-1).double()
    draws = _K6B.joint_draws(model, X_eval, seed=rec.seed)

    rows = []
    for tf in TAU_FRACS:
        theta = tf * mu_max
        p = excursion_probability(draws, theta)
        q = vorobev_expectation(p, draws, theta)
        true_set = truth_eval >= theta
        inter = int((q & true_set).sum())
        union = int((q | true_set).sum())
        row = {"instance": rec.instance, "dim": rec.dim, "sigma": rec.sigma,
               "seed": rec.seed, "arm": rec.arm, "regret": rec.regret,
               "tau_frac": tf, "theta": theta,
               "true_frac_above": float(true_set.double().mean()),
               "n_active": (rec.dim if rec.kept_factors is None
                            else len(rec.kept_factors)),
               "alpha_star": alpha_star(draws, theta),
               "vorobev_deviation": vorobev_deviation(draws, theta),
               "vorobev_expectation_vol": float(q.double().mean()),
               "iou_vorobev_expectation": (inter / union) if union else float("nan"),
               "max_p": float(p.max())}
        for a in ALPHAS:
            ce = conservative_estimate(draws, theta, a)
            n_ce = int(ce.sum())
            row[f"ce_vol_{a}"] = n_ce / ce.numel()
            row[f"ce_empty_{a}"] = n_ce == 0
            row[f"ce_false_in_{a}"] = (float((truth_eval[ce] < theta).double().mean())
                                       if n_ce else float("nan"))
            # CIRCULAR by construction — `conservative_estimate` selects on this. Carried
            # because K6b carries it, so the tautology stays visible in the data.
            row[f"ce_contain_{a}"] = (containment_probability(draws, ce, theta)
                                      if n_ce else float("nan"))
            emp = empirical_containment(ce, truth_eval, theta)
            row[f"ce_empirical_{a}"] = float("nan") if emp is None else float(emp)
        rows.append(row)

    del model, draws
    gc.collect()
    return rows


# ======================================================================================
# THE POSTERIOR-WIDTH COLUMN P4b NEEDS
# ======================================================================================

def mean_posterior_sd(rec: CampaignRecord, X_sub: torch.Tensor) -> float:
    """Mean posterior sd over K6b's 2,000-point subset. **Not a P4 metric.**

    P4b's registered test regresses `alpha_star` on posterior width, and `alpha_star` is
    computed on draws taken over exactly this subset. Measuring the width anywhere else
    would regress two quantities defined on different sets.
    """
    from boec.designspace import gp_adapter
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))
    _, sd = gp_adapter(model).posterior_mean_and_sd(X_sub)
    out = float(sd.mean())
    del model
    gc.collect()
    return out


# ======================================================================================
# DRIVER
# ======================================================================================

def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None,
                    help="(instance, seed) pairs to run; default all 50")
    ap.add_argument("--gate-only", action="store_true",
                    help="regenerate and gate against the committed column; write nothing")
    args = ap.parse_args()

    committed = {(r["instance"], int(r["seed"])): float(r["regret"])
                 for r in committed_rows(E2_GRID)
                 if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12
                 and r["arm"] == ARM}
    keys = sorted(committed)
    if args.limit:
        keys = keys[:args.limit]

    prov = _provenance(sys.argv)
    print(f"P4 · coord at the primary cell · HEAD={prov['git_sha']}")
    print(f"cell d={DIM} sigma={SIGMA} · {len(keys)} (instance, seed) pairs")
    print(f"K6: {GRID_N}-pt Sobol seed {GRID_SEED}, gammas={_K6.GAMMAS}, "
          f"tau_fracs={TAU_FRACS}")
    print(f"K6b: {SUBSET_N}-pt subset, {N_DRAWS} joint draws, alphas={ALPHAS}")
    print(f"gate: committed `coord` regret must reproduce at |delta| = {GATE_TOL:g} "
          f"EXACTLY\n", flush=True)

    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(DIM, SUBSET_N, seed=GRID_SEED)

    k6_rows: list[dict] = []
    k6b_rows: list[dict] = []
    gate: list[dict] = []
    gate_failures: list[dict] = []
    t0 = time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        t = time.time()
        inst = instance_by_id(inst_id, DIM)
        rec = regenerate_coord(inst_id, DIM, SIGMA, seed)

        ref = committed[(inst_id, seed)]
        delta = abs(rec.regret - ref)
        gate.append({"instance": inst_id, "seed": seed, "arm": ARM,
                     "committed": ref, "regenerated": rec.regret, "abs_delta": delta})
        if delta > GATE_TOL:
            gate_failures.append(gate[-1])
            print(f"  !! GATE {ARM} {inst_id} seed={seed} |delta|={delta:.3e}", flush=True)

        if not args.gate_only:
            orc = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
            with torch.no_grad():
                truth = orc.truth(grid).reshape(-1).double()
            k6_rows.extend(score_k6(rec, orc, grid, truth))
            k6b = score_k6b(rec, orc, X_sub, float(inst.optimum_value))
            sd = mean_posterior_sd(rec, X_sub)
            for row in k6b:
                row["mean_posterior_sd"] = sd
            k6b_rows.extend(k6b)
            del truth
            gc.collect()
            print(f"[{i:3d}/{len(keys)}] {inst_id} seed={seed} regret={rec.regret:.4f} "
                  f"|delta|={delta:.1e} a*={k6b[0]['alpha_star']:.3f}.."
                  f"{k6b[-1]['alpha_star']:.3f} ({time.time()-t:.1f}s)", flush=True)
        else:
            print(f"[{i:3d}/{len(keys)}] {inst_id} seed={seed} |delta|={delta:.3e}",
                  flush=True)

    worst = max((g["abs_delta"] for g in gate), default=0.0)
    print(f"\n  gate: {len(gate)} rows checked, worst |delta| = {worst:.3e}, "
          f"{len(gate_failures)} failures")

    if gate_failures:
        print("\n*** STOP. A regenerated `coord` campaign is not the committed campaign, "
              "so every design-space number beside it describes a different experiment. "
              "Reported, not worked around. ***")
        if not args.gate_only:
            _write(prov, k6_rows, k6b_rows, gate, gate_failures)
        raise SystemExit(1)
    if args.gate_only:
        return

    _write(prov, k6_rows, k6b_rows, gate, gate_failures)
    print(f"  {len(k6_rows)} K6 rows + {len(k6b_rows)} K6b rows written to "
          f"{OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.1f} min)")


def _write(prov, k6_rows, k6b_rows, gate, gate_failures) -> None:
    OUT.write_text(json.dumps({
        "provenance": prov,
        "config": {"arm": ARM, "dim": DIM, "sigma": SIGMA, "budget": BUDGET,
                   "grid_n": GRID_N, "grid_seed": GRID_SEED,
                   "gammas": list(_K6.GAMMAS), "tau_fracs": list(TAU_FRACS),
                   "subset_n": SUBSET_N, "n_draws": N_DRAWS, "alphas": list(ALPHAS),
                   "gate_tol": GATE_TOL,
                   "gate_source": "results/e2-grid.json · arm coord · d=6 sigma=0.25",
                   "k6_scorer": "scripts/run_k6_designspace.py::score_campaign (imported)",
                   "k6b_draws": "scripts/run_k6b_conservative.py::joint_draws (imported)"},
        "gate": {"tol": GATE_TOL, "rows_checked": len(gate),
                 "worst_abs_delta": max((g["abs_delta"] for g in gate), default=0.0),
                 "rows": gate},
        "gate_failures": gate_failures,
        "k6_rows": k6_rows, "k6b_rows": k6b_rows}, indent=1))


if __name__ == "__main__":
    main()
