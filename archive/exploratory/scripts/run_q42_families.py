"""Q42 / C.1 — does the E2 reversal reproduce off the Hill oracle? Five families, four cells.

    python scripts/run_q42_families.py --family hartmann6      # one family, all 4 cells
    python scripts/run_q42_families.py --merge                 # reassemble + report

SUPERSEDES Q36, which asked the same question at one cell on two families. This is the
registered version: four cells, four standard families, with the noise-model artefact
Q36 did not control for now fixed.

THE OBJECTION THIS CLOSES
-------------------------
Every headline number in this project comes from a surface we designed, and Q22 measured
it as ~93% additive. A reviewer can say we built the landscape that produced the answer.
Hartmann6 is the direct reply -- non-additive, deceptive, six local optima, fifty years
old and not ours. Levy and Rosenbrock vary the structure further; Ackley is the case
where BO can genuinely lose.

THE NOISE ARTEFACT Q36 DID NOT CONTROL, AND THIS ONE DOES
---------------------------------------------------------
The observation model is `y = f(x)(1 + eps) + eta` -- noise proportional to signal.
Negated, Ackley, Levy and Rosenbrock all have an optimum VALUE of exactly 0, so the
multiplicative term vanishes at the optimum and the hardest region becomes the quietest.
Q36 ran Ackley that way. Every family here is wrapped in `oracles.UnitScaled`, which
rescales so the optimum is exactly 1.0 and the sampled floor ~0 -- the Hill oracle's own
footing, so `sigma_rel` means the same thing in all five.

Regret is therefore in units of each family's own range. That makes the families readable
side by side. **It does not make them poolable and nothing here pools them** -- every
contrast is within a family.

RULE C IS REPORTED IN BOTH FORMS, because Q35 showed the DoE arm's rule-C score moves by
more than the whole gap depending on whether its argmax is constrained to the region
explored. Reporting only the unconstrained form would repeat that strawman on new data.

REGISTERED DECISION RULE, fixed before the run
-----------------------------------------------
"Reversal reproduces" = DoE wins rule A AND BO wins rule C (unconstrained), both CIs
excluding zero -- the pattern E2 shows at d=6 sigma=0.25.

    reproduces on most families   -> the finding is about scoring conventions
    reproduces on none            -> Hill-specific; the paper says so in those words
    reproduces on some            -> report the gradient, do not round it to either

PREDICTION, on the record: it will NOT reproduce on Hartmann6 (Q36 already showed BO
wins everything there at one cell) and will not reproduce cleanly anywhere else either.
What I expect to survive on all five is the SCORING-CONVENTION effect -- constrained
beating unconstrained for the DoE arm -- which Q36 found in the same direction on three
families. I expect the verdict to track landscape structure rather than method.
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

from scipy.stats import wilcoxon                                     # noqa: E402

from boec.campaign import Campaign, CampaignConfig                   # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                     # noqa: E402
from boec.metrics import constrained_argmax                          # noqa: E402
from boec.oracles import (                                          # noqa: E402
    Ackley, Embedded, Hartmann6, Levy, Rosenbrock, UnitScaled)
from boec.rsm import fit_second_order                                # noqa: E402
from boec.torch_oracle import TorchEvaluator                         # noqa: E402

BUDGET = 48
N_REPS = 25
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
N_RESTARTS = 20
RAW_SAMPLES = 4096
RULE = "=" * 104
# Q51: Hartmann6 is defined at d=6 only, so it originally ran at 2 of the 4 cells --
# a gap in the one family that answers "you built the landscape". `Embedded` gives it
# the same structure the Hill oracle already uses at d=8: a fixed active subspace plus
# inert nuisance axes, so the dimension contrast is not confounded with active-count.
FAMILIES = {"hartmann6": lambda d: (Hartmann6() if d == 6
                                    else Embedded(Hartmann6(), dim=d, seed=0)),
            "ackley": lambda d: Ackley(dim=d),
            "levy": lambda d: Levy(dim=d),
            "rosenbrock": lambda d: Rosenbrock(dim=d)}


def run_cell(family: str, dim: int, sigma: float) -> list[dict]:
    inner = FAMILIES[family](dim)
    if inner is None:
        return []                       # Hartmann6 is defined at d=6 only
    oracle = UnitScaled(inner)
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    opt = float(oracle.optimum_value)
    ox = oracle.optimum_x
    centred = ox is not None and bool(np.allclose(np.asarray(ox), 0.5, atol=1e-9))
    rows = []
    for seed in range(N_REPS):
        ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
        c = Campaign(ev, bounds, CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed)).run()
        bo_a = opt - float(reported_best_curve(ev.truth(c.train_X), c.train_Y)[-1])
        model = c.fit()

        def gp_mean(Z: torch.Tensor) -> torch.Tensor:
            with torch.no_grad():
                return model.posterior(Z).mean

        x_bo, _, _ = constrained_argmax(gp_mean, bounds, n_restarts=N_RESTARTS,
                                        raw_samples=RAW_SAMPLES, seed=seed)
        bo_c = opt - float(ev.truth(x_bo.reshape(1, -1)))

        ed = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
        r = run_doe_arm(ed, bounds, truth=ed.truth, budget=BUDGET, seed=seed)
        # D20: was `r.curve_true[-1]`, which is oracle-best. That put THIS arm on a
        # different rule from `bo_a` fifteen lines above, inside one loop, and the gap
        # ran entirely in DoE's favour (+0.041 Levy, +0.044 Rosenbrock, +0.018 Hartmann6).
        doe_a = opt - float(
            reported_best_curve(ed.truth(r.X_visited), r.Y_visited)[-1])
        doe_cu = opt - float(ed.truth(r.confirmation_x.unsqueeze(0)))

        kept = list(r.kept_factors)
        # Q51: the screen keeps a fixed 4 factors. Hartmann6 has 6 active ones, so it
        # must discard real signal; at d=8 it can also waste slots on the inert axes.
        act = getattr(inner, "active", None)
        act = set(range(dim)) if act is None else set(int(i) for i in act)
        n_kept_active = len(set(kept) & act)
        s2 = slice(r.n_stage1, r.n_stage1 + r.n_stage2)
        try:
            fit = fit_second_order(r.X_visited[s2][:, kept], r.Y_visited[s2])
            x_con, _, _ = constrained_argmax(fit.predict, r.stage2_bounds,
                                             n_restarts=N_RESTARTS,
                                             raw_samples=RAW_SAMPLES, seed=seed)
            full = torch.tensor([r.dropped_held_at.get(i, 0.0) for i in range(dim)],
                                dtype=torch.double)
            full[kept] = x_con.double().reshape(-1)
            doe_cc = opt - float(ed.truth(full.unsqueeze(0)))
            fail = None
        except Exception as exc:                          # noqa: BLE001 - recorded
            doe_cc, fail = None, f"{type(exc).__name__}: {exc}"

        rows.append(dict(family=family, dim=dim, sigma=sigma, seed=seed,
                         bo_a=bo_a, bo_c=bo_c, doe_a=doe_a,
                         doe_c_unconstrained=doe_cu, doe_c_constrained=doe_cc,
                         constrained_failure=fail,
                         stationary_kind=r.stationary_kind,
                         n_kept_active=n_kept_active, n_active=len(act),
                         kept_factors=kept,
                         optimum_at_design_centre=centred,
                         scale=oracle.scale,
                         confirmation_inside_stage2=bool(r.confirmation_inside_stage2)))
    return rows


def _paired(rows, a, b):
    va = np.array([r[a] for r in rows if r[a] is not None and r[b] is not None])
    vb = np.array([r[b] for r in rows if r[a] is not None and r[b] is not None])
    if va.size < 3:
        return None
    d = va - vb
    m, lo, hi = instance_bootstrap(d, n_boot=2000)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:
        p = float("nan")
    return dict(diff=m, lo=lo, hi=hi, p=p, n=int(d.size),
                verdict="BO better" if lo > 0 else ("DoE better" if hi < 0 else "null"))


def report(rows, family, dim, sigma) -> dict:
    print(f"\n{RULE}\nQ42 · {family} · d={dim} · sigma={sigma} · {len(rows)} reps\n{RULE}")
    print(f"{'arm / rule':<42}{'mean regret':>13}{'median':>10}")
    for k, lab in (("bo_a", "BO   rule A (best observed)"),
                   ("doe_a", "DoE  rule A (best observed)"),
                   ("bo_c", "BO   rule C (GP posterior-mean argmax)"),
                   ("doe_c_unconstrained", "DoE  rule C UNCONSTRAINED"),
                   ("doe_c_constrained", "DoE  rule C CONSTRAINED")):
        v = np.array([r[k] for r in rows if r[k] is not None])
        if v.size:
            print(f"{lab:<42}{v.mean():>13.4f}{np.median(v):>10.4f}")
    out = {}
    print(f"\n  {'contrast':<32}{'DoE - BO  (>0 = BO better)':>46}")
    for a, b, tag in (("doe_a", "bo_a", "rule A"),
                      ("doe_c_unconstrained", "bo_c", "rule C unconstrained"),
                      ("doe_c_constrained", "bo_c", "rule C constrained")):
        r = _paired(rows, a, b)
        out[tag] = r
        if r:
            print(f"  {tag:<32}{r['diff']:>+11.4f} [{r['lo']:>+8.4f},{r['hi']:>+8.4f}] "
                  f"p={r['p']:<8.4f} {r['verdict']}")
    kinds = {}
    for r in rows:
        kinds[r["stationary_kind"]] = kinds.get(r["stationary_kind"], 0) + 1
    print(f"\n  fitted-surface stationary point: {kinds}")
    if rows[0].get("n_kept_active") is not None:
        ka = np.mean([r["n_kept_active"] for r in rows])
        print(f"  DoE screen kept {ka:.2f} of its 4 slots on genuinely active factors "
              f"({rows[0]['n_active']} of {rows[0]['dim']} are active)")
    if rows[0]["optimum_at_design_centre"]:
        print("  *** rule A VOID: this function's optimum is the exact box centre, and\n"
              "      every screen and CCD includes centre runs, so the DoE design contains\n"
              "      the answer for free. Rule C still means something.")
    a_doe = out.get("rule A") and out["rule A"]["verdict"] == "DoE better"
    c_bo = out.get("rule C unconstrained") and out["rule C unconstrained"]["verdict"] == "BO better"
    rep = bool(a_doe and c_bo) and not rows[0]["optimum_at_design_centre"]
    print(f"\n  REVERSAL REPRODUCES: {'YES' if rep else 'NO'}")
    return dict(family=family, dim=dim, sigma=sigma, contrasts=out, reproduces=rep,
                voided=rows[0]["optimum_at_design_centre"], kinds=kinds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=sorted(FAMILIES))
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    outdir = ROOT / "results"

    if args.merge:
        allrows, summ = [], []
        for f in sorted(FAMILIES):
            p = outdir / f"q42-families-{f}.json"
            if not p.exists():
                print(f"  MISSING shard: {p.name}")
                continue
            allrows.extend(json.loads(p.read_text()))
        for f in sorted(FAMILIES):
            for dim, sigma in CELLS:
                sub = [r for r in allrows if r["family"] == f and r["dim"] == dim
                       and abs(r["sigma"] - sigma) < 1e-12]
                if sub:
                    summ.append(report(sub, f, dim, sigma))
        (outdir / "q42-families.json").write_text(
            json.dumps(dict(rows=allrows, summary=summ), indent=1))
        rep = [s for s in summ if s["reproduces"]]
        print(f"\n{RULE}\nREVERSAL REPRODUCES IN {len(rep)} OF {len(summ)} "
              f"family-cells\n{RULE}")
        for s in summ:
            flag = "VOID(centred)" if s["voided"] else ("YES" if s["reproduces"] else "no")
            print(f"  {s['family']:<12} d={s['dim']} s={s['sigma']:<5} -> {flag}")
        return

    t0 = time.time()
    out = outdir / f"q42-families-{args.family}.json"
    # Checkpoint per CELL, not only at the end. Q51's Hartmann6 re-run spent 5.25 hours
    # on its first cell under heavy machine contention while holding every row in
    # memory, because this wrote once after all four. A kill at that point would have
    # cost the lot. Cells already present are skipped, so a restart resumes.
    rows = json.loads(out.read_text()) if out.exists() else []
    have = {(r["dim"], round(float(r["sigma"]), 6)) for r in rows}
    for dim, sigma in CELLS:
        if (dim, round(float(sigma), 6)) in have:
            print(f"  {args.family} d={dim} s={sigma} already present, skipping",
                  flush=True)
            continue
        rows.extend(run_cell(args.family, dim, sigma))
        out.write_text(json.dumps(rows, indent=1))
        print(f"  {args.family} d={dim} s={sigma} done ({time.time()-t0:.0f}s), "
              f"checkpointed {len(rows)} rows", flush=True)
    print(f"  -> results/q42-families-{args.family}.json  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
