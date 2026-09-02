"""Q45 / C.2 — is Q34's design-effect result an artefact of a model neither design supports?

    python scripts/run_q45_fourfactor_refit.py     # log at results/q45-fourfactor-refit.log

THE CONFOUND
------------
Q34's polynomial design contrast (cell 3 − cell 6) compares a **four-factor** quadratic
fitted on the DoE arm's stage-2 data against a **six-factor** quadratic fitted on the BO
arm's 48 points. Those are different models, so the contrast confounds design with model
dimensionality — flagged in Q34's own output as the weakest of its four contrasts.

Q44 then made it worse-looking and clearer: at the six-factor model the CCD is
**singular in 50/50 runs** while the adaptive design is singular in 0/50. So the
six-factor comparison is not a fair test of anything; it measures a design against a
model it was never built for.

THE FIX
-------
Refit **both** polynomial cells on the **same four factors** — the ones the DoE arm's own
screen kept — so the model is held fixed and only the design varies. Cell 3 already is
that model. Cell 6 is refitted from the BO arm's points projected onto those same four
factors, with the dropped factors held where the DoE arm held them, so the recommendation
is evaluated at a comparable full-dimensional recipe.

📌 REGISTERED PREDICTION, before the run
----------------------------------------
**1. Cell 6 improves a lot.** Its six-factor version carries 0.58–0.70 regret. A
four-factor quadratic on 48 well-spread points has 15 parameters and 33 residual df
instead of 45 and 3, so it should be far better determined. I expect a large improvement.

**2. It will still be much worse than the GP on the same data (cell 4).** The polynomial's
failure mode is geometric — an indefinite Hessian has no interior maximum, so its argmax
reaches a boundary — and that is a property of the fitted surface, not of how well the
coefficients are estimated. Better conditioning should not repair it.

**3. The design contrast stays small relative to the surrogate effect.** Q34 put the
surrogate effect at 0.16–0.29 and the design effect at 0.00–0.20. I expect the cleaned-up
3−6 contrast to land below the surrogate effect at the primary cell.

**The brief predicts the design null STRENGTHENS. I am predicting something weaker and
different — that the contrast becomes measurable but stays subordinate.** Recorded so the
disagreement is scoreable either way.

**What would falsify me:** cell 6, refitted, coming close to cell 4. That would mean the
polynomial's disadvantage was estimation error rather than geometry, and the whole
saddle argument would need rewriting.
"""

from __future__ import annotations

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

from scipy.stats import wilcoxon                              # noqa: E402

from boec.campaign import Campaign, CampaignConfig            # noqa: E402
from boec.diagnostics import instance_bootstrap               # noqa: E402
from boec.doe import run_doe_arm                              # noqa: E402
from boec.metrics import constrained_argmax                   # noqa: E402
from boec.oracles import load_ensemble                        # noqa: E402
from boec.rsm import fit_second_order                         # noqa: E402
from boec.torch_oracle import BiphasicOracle                  # noqa: E402

BUDGET, N_INSTANCES, N_SEEDS = 48, 25, 2
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
N_RESTARTS, RAW_SAMPLES = 20, 4096
RULE = "=" * 96


def run_cell(dim: int, sigma: float) -> list[dict]:
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    rows = []
    for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
        for seed in range(N_SEEDS):
            opt = float(inst.optimum_value)
            o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            r = run_doe_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=seed)
            kept = list(r.kept_factors)

            ob = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            c = Campaign(ob, bounds, CampaignConfig(d=dim, budget=BUDGET, q=4,
                                                    seed=seed)).run()

            def lift(x_kept: torch.Tensor) -> torch.Tensor:
                full = torch.tensor([r.dropped_held_at.get(i, 0.0) for i in range(dim)],
                                    dtype=torch.double)
                full[kept] = x_kept.double().reshape(-1)
                return full.unsqueeze(0)

            search = torch.stack([bounds[0, kept], bounds[1, kept]])

            # cell 3 — unchanged: the DoE arm's own reduced surface
            row = dict(instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                       n_kept=len(kept),
                       cell3_doe_poly=opt - float(o.truth(r.confirmation_x.unsqueeze(0))))

            # cell 6 REFIT — the same reduced model, on the BO arm's points
            try:
                fit6 = fit_second_order(c.train_X[:, kept], c.train_Y)
                x6, _, _ = constrained_argmax(fit6.predict, search,
                                              n_restarts=N_RESTARTS,
                                              raw_samples=RAW_SAMPLES, seed=seed)
                row["cell6_refit"] = opt - float(ob.truth(lift(x6)))
                row["cell6_refit_failure"] = None
            except Exception as exc:                       # noqa: BLE001 - recorded
                row["cell6_refit"] = None
                row["cell6_refit_failure"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
    return rows


def paired(rows, a, b):
    insts = sorted({r["instance"] for r in rows})
    va, vb = [], []
    for i in insts:
        g = [r for r in rows if r["instance"] == i]
        if any(r[a] is None or r[b] is None for r in g):
            continue
        va.append(np.mean([r[a] for r in g]))
        vb.append(np.mean([r[b] for r in g]))
    if len(va) < 3:
        return None
    d = np.array(va) - np.array(vb)
    m, lo, hi = instance_bootstrap(d, n_boot=2000)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:
        p = float("nan")
    return dict(diff=float(m), lo=float(lo), hi=float(hi), p=p, n=int(len(d)))


def main() -> None:
    q34 = {(r["instance"], r["dim"], r["sigma"], r["seed"]): r
           for r in json.loads((ROOT / "results" / "q34-factorial.json").read_text())}
    out, t0 = [], time.time()
    print(f"{RULE}\nQ45 / C.2 — polynomial design contrast at a model BOTH designs "
          f"support\n{RULE}")
    for dim, sigma in CELLS:
        rows = run_cell(dim, sigma)
        for r in rows:
            k = (r["instance"], r["dim"], r["sigma"], r["seed"])
            src = q34.get(k)
            r["cell6_sixfactor"] = src["cell6_bo_poly"] if src else None
            r["cell4_bo_gp"] = src["cell4_bo_gp"] if src else None
        out.extend(rows)

        def mean(k):
            v = [r[k] for r in rows if r[k] is not None]
            return float(np.mean(v)) if v else float("nan")

        fails = sum(1 for r in rows if r["cell6_refit_failure"])
        print(f"\n  d={dim} sigma={sigma}   (kept factors: median "
              f"{np.median([r['n_kept'] for r in rows]):.0f} of {dim})")
        print(f"    cell 3  DoE / 4-factor poly            {mean('cell3_doe_poly'):.4f}")
        print(f"    cell 6  BO  / 6-factor poly  (Q34)     {mean('cell6_sixfactor'):.4f}")
        print(f"    cell 6  BO  / 4-FACTOR poly  REFIT     {mean('cell6_refit'):.4f}"
              f"    <- the fix")
        print(f"    cell 4  BO  / GP                       {mean('cell4_bo_gp'):.4f}")
        for a, b, lab in (("cell3_doe_poly", "cell6_refit", "3-6 DESIGN, model now fixed"),
                          ("cell6_refit", "cell6_sixfactor", "refit - sixfactor (the fix)"),
                          ("cell4_bo_gp", "cell6_refit", "4-6 SURROGATE, design fixed")):
            r = paired(rows, a, b)
            if r:
                v = "a better" if r["hi"] < 0 else ("b better" if r["lo"] > 0 else "null")
                print(f"      {lab:<30}{r['diff']:>+9.4f} [{r['lo']:>+8.4f},"
                      f"{r['hi']:>+8.4f}] p={r['p']:<8.4f} {v}")
        if fails:
            print(f"      refit hard failures: {fails}/{len(rows)}")
    (ROOT / "results" / "q45-fourfactor-refit.json").write_text(json.dumps(out, indent=1))
    print(f"\n  [{time.time()-t0:.0f}s]  written to results/q45-fourfactor-refit.json")


if __name__ == "__main__":
    main()
