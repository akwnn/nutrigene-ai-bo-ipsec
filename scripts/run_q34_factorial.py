"""Q34 / T1.1 — the design x surrogate x rule factorial, untangling E2's confound.

    python scripts/run_q34_factorial.py                 # primary cell, d=6 sigma=0.25
    python scripts/run_q34_factorial.py --all-cells     # all four

PRE-REGISTERED in OPEN-QUESTIONS Q34, committed before this ran. The prediction and the
decision rule are both in that entry; do not read the table below before reading them.

WHAT THIS IS FOR
----------------
E2 compares (structured design + polynomial + rule) against (adaptive design + GP +
rule) and attributes the reversal to model class. Three factors move at once. Under
rule A the surrogate drops out -- best-observed is a property of the design alone -- so
the factorial collapses to six quantities, two of which have never been computed:

    cell 3   DoE design  + polynomial + recommended     (the stage-4 point)
    cell 4   BO design   + GP         + recommended     (Q29's rule C)
    cell 5   DoE design  + GP         + recommended     NEW -- the decisive cell
    cell 6   BO design   + polynomial + recommended     NEW

All four are computed HERE, in one execution, with ONE locator. Cells 3 and 4 already
had numbers, but those were produced with the asymmetric locator T1.4c fixed (BO side
unseeded at a 16x smaller Sobol screen), so reusing them would embed a known artefact in
three of the four contrasts. This run supersedes Q29's rule-C table.

WHAT CELL 5 AND CELL 6 ACTUALLY DO
----------------------------------
Both fit the *other* arm's surrogate to the *same* collected data, changing nothing else:

    cell 5   build_gp(X_doe, Y_doe, Yvar_doe)      -> constrained_argmax -> truth()
    cell 6   fit_second_order(X_bo, Y_bo)          -> constrained_argmax -> truth()

`Yvar` for the DoE arm is recomputed with `_plug_in_yvar`, which is a deterministic
function of the observed y -- NOT by re-evaluating the oracle, which would draw fresh
noise and quietly make cell 5 a different experiment from cell 1.

Cell 6 is expected to fail sometimes: a full second-order model needs p=28 terms at d=6
and p=45 at d=8 against n=48, and BO clusters its points by design. `fit_second_order`
raises on rank deficiency rather than reaching for a pseudo-inverse. **Those failures are
recorded and reported as a rate, never dropped** -- a design-dependent failure rate is
the quantitative form of "you cannot fit a response surface to adaptively-collected
data", which is itself a result.
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

from scipy.stats import wilcoxon                                        # noqa: E402

from boec.campaign import Campaign, CampaignConfig                      # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve    # noqa: E402
from boec.doe import run_doe_arm                                        # noqa: E402
from boec.metrics import constrained_argmax                             # noqa: E402
from boec.oracles import load_ensemble                                  # noqa: E402
from boec.rsm import fit_second_order, second_order_design_matrix       # noqa: E402
from boec.surrogate import build_gp                                     # noqa: E402
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar             # noqa: E402

BUDGET = 48
N_INSTANCES = 25
N_SEEDS = 2
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))

#: One locator, one screening budget, for every cell. Registered in Q34 and asserted
#: in tests/test_q34_factorial.py. These are `constrained_argmax`'s defaults, which is
#: what the DoE arm receives through `over_prediction_at_constrained_argmax`.
N_RESTARTS = 20
RAW_SAMPLES = 4096
RULE = "=" * 96


def _unit_bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _gp_recommendation(X, Y, Yvar, bounds, seed):
    """Fit a production GP to whatever data it is handed, and ask where the optimum is."""
    model = build_gp(X, Y, Yvar, bounds)

    def predict(Z: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return model.posterior(Z).mean

    x, _, _ = constrained_argmax(predict, bounds, n_restarts=N_RESTARTS,
                                 raw_samples=RAW_SAMPLES, seed=seed)
    return x.reshape(1, -1)


def _poly_recommendation(X, Y, bounds, seed):
    """Same, for a full second-order surface. Returns (x, cond) or (None, cond, reason)."""
    M = second_order_design_matrix(X)
    cond = float(np.linalg.cond(M.numpy() if torch.is_tensor(M) else M))
    fit = fit_second_order(X, Y)          # raises on rank deficiency; caller records it
    x, _, _ = constrained_argmax(fit.predict, bounds, n_restarts=N_RESTARTS,
                                 raw_samples=RAW_SAMPLES, seed=seed)
    return x.reshape(1, -1), cond


def run_cell(dim: int, sigma: float) -> list[dict]:
    bounds = _unit_bounds(dim)
    rows: list[dict] = []
    for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
        for seed in range(N_SEEDS):
            opt = float(inst.optimum_value)
            row = dict(instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed)

            # ---- the BO design -------------------------------------------------
            o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            c = Campaign(o, bounds, CampaignConfig(d=dim, budget=BUDGET, q=4,
                                                   seed=seed)).run()
            row["cell2_bo_observed"] = opt - float(
                reported_best_curve(o.truth(c.train_X), c.train_Y)[-1])

            # cell 4 — BO design, GP surrogate
            x4 = _gp_recommendation(c.train_X, c.train_Y, c.train_Yvar, bounds, seed)
            row["cell4_bo_gp"] = opt - float(o.truth(x4))

            # cell 6 — BO design, POLYNOMIAL surrogate. May legitimately fail.
            try:
                x6, cond6 = _poly_recommendation(c.train_X, c.train_Y, bounds, seed)
                row["cell6_bo_poly"] = opt - float(o.truth(x6))
                row["cell6_cond"] = cond6
                row["cell6_failure"] = None
            except Exception as exc:                       # noqa: BLE001 - recorded, not swallowed
                row["cell6_bo_poly"] = None
                row["cell6_cond"] = None       # type: ignore[assignment]
                row["cell6_failure"] = f"{type(exc).__name__}: {exc}"

            # ---- the DoE design ------------------------------------------------
            od = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            r = run_doe_arm(od, bounds, truth=od.truth, budget=BUDGET, seed=seed)
            row["cell1_doe_observed"] = opt - float(
                reported_best_curve(od.truth(r.X_visited), r.Y_visited)[-1])

            # cell 3 — DoE design, polynomial surrogate: the arm's own stage-4 point
            row["cell3_doe_poly"] = opt - float(od.truth(r.confirmation_x.unsqueeze(0)))

            # cell 5 — DoE design, GP surrogate. THE DECISIVE CELL.
            # Yvar is recomputed from the observed y, not re-drawn from the oracle.
            yvar_doe = torch.from_numpy(_plug_in_yvar(
                r.Y_visited.numpy(), od.sigma_rel, od.sigma_add))
            x5 = _gp_recommendation(r.X_visited, r.Y_visited, yvar_doe, bounds, seed)
            row["cell5_doe_gp"] = opt - float(od.truth(x5))

            # Conditioning of a FULL d-dimensional second-order model on each design's
            # 48 points. Like-for-like with cell 6, and NOT the model the DoE arm fits
            # -- that one is reduced to the kept factors after screening (doe.py:329),
            # which is exactly how the pipeline avoids the singularity measured here.
            try:
                Mdoe = second_order_design_matrix(r.X_visited)
                row["cond_full_poly_on_doe_points"] = float(np.linalg.cond(
                    Mdoe.numpy() if torch.is_tensor(Mdoe) else Mdoe))
            except Exception:                              # noqa: BLE001
                row["cond_full_poly_on_doe_points"] = None
            row["n_kept_factors"] = len(r.kept_factors)

            rows.append(row)
    return rows


def _per_instance(rows: list[dict], key: str) -> tuple[list[str], np.ndarray, int]:
    """One number per instance, seeds averaged. Instances with any missing seed drop out.

    The count of dropped instances is returned and printed -- it is the cell-6 failure
    rate expressed at the level the inference actually runs at.
    """
    ids, vals, dropped = [], [], 0
    for i in sorted({r["instance"] for r in rows}):
        got = [r[key] for r in rows if r["instance"] == i]
        if any(v is None for v in got):
            dropped += 1
            continue
        ids.append(i)
        vals.append(float(np.mean(got)))
    return ids, np.array(vals), dropped


def _contrast(rows, a: str, b: str) -> str:
    """`a` minus `b`, paired on the instances where BOTH are defined."""
    common = sorted({r["instance"] for r in rows})
    pa, pb = [], []
    for i in common:
        ga = [r[a] for r in rows if r["instance"] == i]
        gb = [r[b] for r in rows if r["instance"] == i]
        if any(v is None for v in ga) or any(v is None for v in gb):
            continue
        pa.append(np.mean(ga))
        pb.append(np.mean(gb))
    if len(pa) < 3:
        return f"{'n<3, not estimable':>44}"
    d = np.array(pa) - np.array(pb)
    m, lo, hi = instance_bootstrap(d, n_boot=2000)
    try:
        p = wilcoxon(d).pvalue
    except ValueError:
        p = float("nan")
    verdict = "a worse" if lo > 0 else ("a better" if hi < 0 else "null")
    return f"{m:>+9.4f} [{lo:>+8.4f},{hi:>+8.4f}] p={p:<8.4f} n={len(d):<3} {verdict}"


def report(rows: list[dict], dim: int, sigma: float) -> None:
    print(f"\n{RULE}\nQ34 · d={dim} · sigma={sigma} · {N_INSTANCES} instances x "
          f"{N_SEEDS} seeds{'   <-- REGISTERED PRIMARY CELL' if (dim, sigma) == (6, 0.25) else ''}\n{RULE}")

    labels = [("cell1_doe_observed", "1  DoE  / --         / observed"),
              ("cell2_bo_observed", "2  BO   / --         / observed"),
              ("cell3_doe_poly", "3  DoE  / polynomial / recommended"),
              ("cell4_bo_gp", "4  BO   / GP         / recommended"),
              ("cell5_doe_gp", "5  DoE  / GP         / recommended  <-- NEW"),
              ("cell6_bo_poly", "6  BO   / polynomial / recommended  <-- NEW")]
    print(f"{'cell':<38}{'mean regret':>13}{'median':>10}{'n':>5}{'dropped':>9}")
    for key, label in labels:
        _, v, dropped = _per_instance(rows, key)
        if v.size == 0:
            print(f"{label:<38}{'ALL FAILED':>13}{'':>10}{0:>5}{dropped:>9}")
            continue
        print(f"{label:<38}{v.mean():>13.4f}{np.median(v):>10.4f}{v.size:>5}{dropped:>9}")

    print(f"\n  {'contrast':<34}{'paired difference (>0 = first is worse)':>44}")
    for a, b, name in (("cell5_doe_gp", "cell3_doe_poly", "5-3 surrogate @ DoE  PRIMARY"),
                       ("cell4_bo_gp", "cell6_bo_poly", "4-6 surrogate @ BO"),
                       ("cell4_bo_gp", "cell5_doe_gp", "4-5 design @ GP"),
                       ("cell3_doe_poly", "cell6_bo_poly", "3-6 design @ polynomial"),
                       ("cell1_doe_observed", "cell2_bo_observed", "1-2 design @ observed (rule A)")):
        print(f"  {name:<34}{_contrast(rows, a, b)}")

    fails = [r for r in rows if r["cell6_failure"] is not None]
    print(f"\n  cell 6 hard failures: {len(fails)}/{len(rows)} runs "
          f"({100 * len(fails) / max(len(rows), 1):.1f}%)")
    for reason in sorted({f["cell6_failure"].split(" (")[0] for f in fails}):
        n = sum(1 for f in fails if f["cell6_failure"].startswith(reason))
        print(f"      {n:>3}x  {reason}")
    for key, label in (("cond_full_poly_on_doe_points", "DoE design"),
                       ("cell6_cond", "BO design")):
        c = [r[key] for r in rows if r.get(key) is not None]
        if c:
            print(f"  cond(second-order design matrix), {label:<11}: "
                  f"median {np.median(c):.3e}  max {max(c):.3e}  n={len(c)}")
    kept = [r["n_kept_factors"] for r in rows if r.get("n_kept_factors") is not None]
    if kept:
        print(f"  DoE factors kept by the screen: median {np.median(kept):.1f} "
              f"of {dim}")
    print("  NOTE both conditioning figures are for a FULL d-dimensional second-order\n"
          "  model on that design's 48 points, so they are like-for-like with cell 6.\n"
          "  Neither is the model the DoE arm fits: after screening it fits a REDUCED\n"
          "  surface on the kept factors only, which is precisely how the pipeline\n"
          "  avoids the singularity above. Cell 3 is therefore a lower-dimensional\n"
          "  polynomial than cell 6, and the 3-6 design contrast confounds design with\n"
          "  model dimensionality. It is the weakest of the four; the registered\n"
          "  primary (5-3) does not depend on it.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-cells", action="store_true")
    args = ap.parse_args()

    cells = list(CELLS) if args.all_cells else [(6, 0.25)]
    everything: list[dict] = []
    t0 = time.time()
    for dim, sigma in cells:
        rows = run_cell(dim, sigma)
        everything.extend(rows)
        report(rows, dim, sigma)
        print(f"\n  [{time.time() - t0:.0f}s elapsed]", flush=True)

    out = ROOT / "results" / "q34-factorial.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(everything, indent=1))
    print(f"\n  written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
