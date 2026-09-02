"""Q27 — the d=8 sequential-DoE arm. Q24's missing comparison.

Pre-registered in `docs/OPEN-QUESTIONS.md` Q27, committed before this ran. Check
this file's first output line against that entry's commit timestamp.

**This adds an arm. It does not re-run E2.** Every other d=8 number is read from
`results/e2-grid.json` exactly as stored — which is only legitimate if this code
still produces those numbers, so the run refuses to report anything until it has
regenerated them and found them identical.

Two fidelity tiers, both blocking:

  * the cheap arms (random, sobol, lhs, coord) — all 400 stored d=8 rows;
  * qLogEI and qLogNEI — a declared subsample, because each campaign is ~7s and
    the full set is ~25 minutes. **The subsample is fixed here, in code, not
    chosen after looking.**

If either fails the script exits without writing a result. A DoE number compared
against a stale qLogEI number is not a comparison.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boec.baselines import coordinate_descent            # noqa: E402
from boec.campaign import Campaign, CampaignConfig       # noqa: E402
from boec.diagnostics import instance_bootstrap          # noqa: E402
from boec.doe import STAGE1_FRACTION, run_doe_arm        # noqa: E402
from boec.optimizers import AcqConfig                    # noqa: E402
from boec.oracles import load_ensemble                   # noqa: E402
from boec.torch_oracle import BiphasicOracle             # noqa: E402
from run_e2 import (                                     # noqa: E402
    BUDGET, N_INSTANCES, N_SEEDS, SIGMAS, STATIC,
    scored_curve, static_curve, unit_bounds,
)

DIM = 8
GRID = Path("results/e2-grid.json")
OUT = Path("results/e2-doe-d8.json")

#: Fixed before the run. The first five instances of the ensemble, both seeds,
#: both noise levels — 20 campaigns per adaptive arm. Not chosen after seeing
#: anything; `load_ensemble` returns a fixed order and this is its head.
FIDELITY_SUBSAMPLE = 5

#: n_init at d=8 is 2d+2. Used only for the AUC segment, matching run_e2.py.
N_INIT = 2 * DIM + 2


def _stored() -> dict:
    rows = json.loads(GRID.read_text())
    return {(r["instance"], r["sigma"], r["seed"], r["arm"]): r
            for r in rows if r["dim"] == DIM}


def _fail(msg: str) -> None:
    print(f"\nFIDELITY FAILED — nothing written.\n{msg}")
    raise SystemExit(1)


def check_fidelity(ens, stored) -> None:
    """Regenerate stored d=8 rows. Any mismatch voids the run."""
    bounds = unit_bounds(DIM)

    worst_cheap, n_cheap = 0.0, 0
    for sigma in SIGMAS:
        for inst in ens:
            for seed in range(N_SEEDS):
                for arm in STATIC:
                    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                    got = float(static_curve(o, bounds, arm, BUDGET, seed)[-1])
                    key = (inst.instance_id, sigma, seed, arm)
                    worst_cheap = max(worst_cheap, abs(got - stored[key]["best"]))
                    n_cheap += 1
                o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                cd = coordinate_descent(o, bounds, budget=BUDGET, seed=seed)
                got = float(scored_curve(o, cd.X, cd.Y)[-1])
                key = (inst.instance_id, sigma, seed, "coord")
                worst_cheap = max(worst_cheap, abs(got - stored[key]["best"]))
                n_cheap += 1
    print(f"  cheap arms : {n_cheap} rows, max |delta| = {worst_cheap:.3e}")
    if worst_cheap > 1e-9:
        _fail(f"static/coord arms drifted by {worst_cheap:.3e}")

    worst_bo, n_bo = 0.0, 0
    for sigma in SIGMAS:
        for inst in ens[:FIDELITY_SUBSAMPLE]:
            for seed in range(N_SEEDS):
                for arm in ("qlogei", "qlognei"):
                    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                    cfg = CampaignConfig(d=DIM, budget=BUDGET, q=4, seed=seed,
                                         acq=AcqConfig(kind=arm))
                    c = Campaign(o, unit_bounds(DIM), cfg)
                    c.run()
                    got = float(scored_curve(o, c.train_X, c.train_Y)[-1])
                    key = (inst.instance_id, sigma, seed, arm)
                    worst_bo = max(worst_bo, abs(got - stored[key]["best"]))
                    n_bo += 1
    print(f"  BO arms    : {n_bo} rows ({FIDELITY_SUBSAMPLE} instances), "
          f"max |delta| = {worst_bo:.3e}")
    if worst_bo > 1e-9:
        _fail(f"qLogEI/qLogNEI drifted by {worst_bo:.3e} — the comparison target moved")


def run_arm(ens) -> list[dict]:
    bounds = unit_bounds(DIM)
    rows = []
    for sigma in SIGMAS:
        for inst in ens:
            for seed in range(N_SEEDS):
                o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                r = run_doe_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=seed)
                curve = scored_curve(o, r.X_visited, r.Y_visited)
                rows.append(dict(
                    instance=inst.instance_id, dim=DIM, sigma=sigma, seed=seed,
                    arm="doe",
                    best=float(curve[-1]),
                    regret=float(inst.optimum_value - curve[-1]),
                    auc_post_init=float(np.trapezoid(curve[N_INIT:])
                                        / max(len(curve) - N_INIT - 1, 1)),
                    n_derived_stage1=r.n_derived_stage1,
                    kept_factors=list(r.kept_factors),
                    active_factors=[int(i) for i in inst.active_idx],
                    over_prediction=r.over_prediction,
                    # POST-HOC, declared as such in Q27's result entry. The arm's
                    # *output* is the stage-4 recipe, but `scored_curve` reports
                    # best-so-far over all 48 points and the confirmation is never
                    # the observed argmax -- so `regret` above scores the arm's
                    # design coverage, not the thing the method produces. Q20 §3
                    # raised exactly this ambiguity and left it unregistered.
                    predicted_y=r.predicted_y,
                    confirmation_true=float(r.predicted_y - r.over_prediction),
                    regret_at_confirmation=float(
                        inst.optimum_value - (r.predicted_y - r.over_prediction)),
                    inside_stage2=bool(r.confirmation_inside_stage2),
                    on_stage2_boundary=bool(r.confirmation_on_stage2_boundary),
                    stationary_kind=r.stationary_kind,
                ))
        print(f"  sigma={sigma} done ({len(rows)} rows)", flush=True)
    return rows


def _per_instance(rows, insts, key="regret") -> np.ndarray:
    """One number per instance, averaged over seeds. Effective n = 25, not 50."""
    return np.array([np.mean([r[key] for r in rows if r["instance"] == i])
                     for i in insts])


def report(doe_rows, stored) -> None:
    arms = ["qlogei", "qlognei", "random", "sobol", "lhs", "coord"]
    for sigma in SIGMAS:
        sub_doe = [r for r in doe_rows if r["sigma"] == sigma]
        insts = sorted({r["instance"] for r in sub_doe})
        primary = " <-- Q27 PRIMARY" if sigma == 0.25 else " (secondary)"
        print(f"\n{'=' * 84}\nQ27 · d={DIM} · sigma_rel={sigma} · "
              f"{len(insts)} instances x {N_SEEDS} seeds{primary}\n{'=' * 84}")

        per = {"doe": _per_instance(sub_doe, insts)}
        for a in arms:
            rows_a = [stored[(i, sigma, s, a)] for i in insts for s in range(N_SEEDS)]
            per[a] = _per_instance(rows_a, insts)

        print(f"{'arm':>9} {'mean regret':>12} {'median':>9} "
              f"{'AUC post-init':>14}")
        auc_doe = np.median([r["auc_post_init"] for r in sub_doe])
        for a in ["doe"] + arms:
            if a == "doe":
                auc = auc_doe
            else:
                auc = np.median([stored[(i, sigma, s, a)]["auc_post_init"]
                                 for i in insts for s in range(N_SEEDS)])
            mark = "  <-- new" if a == "doe" else ""
            print(f"{a:>9} {per[a].mean():>12.4f} {np.median(per[a]):>9.4f} "
                  f"{auc:>14.4f}{mark}")

        print(f"\n  paired on instance, DoE minus arm (negative = DoE has LESS "
              f"regret), n={len(insts)}:")
        for a in arms:
            d_ = per["doe"] - per[a]
            m, lo, hi = instance_bootstrap(d_, n_boot=2000)
            try:
                p = wilcoxon(d_).pvalue
            except ValueError:
                p = float("nan")
            tag = "  <-- THE Q27 PRIMARY" if (a == "qlogei" and sigma == 0.25) else ""
            print(f"    vs {a:>8}: {m:>+8.4f}  [{lo:>+8.4f}, {hi:>+8.4f}]  "
                  f"wilcoxon p={p:.4f}{tag}")

        # Minimum detectable effect, so a null can be read as a null rather than
        # as evidence of no difference. Bootstrap the paired sd against qLogEI.
        d_ = per["doe"] - per["qlogei"]
        mde = 2.8 * d_.std(ddof=1) / np.sqrt(len(d_))   # ~80% power, alpha=0.05
        print(f"\n  minimum detectable paired difference vs qLogEI "
              f"(80% power, alpha=0.05): {mde:.4f}")

        # What the arm did, descriptively. These are the escape statistics the
        # pipeline produces anyway; they are not the endpoint.
        hit = np.mean([len(set(r["kept_factors"]) & set(r["active_factors"]))
                       / len(r["active_factors"]) for r in sub_doe])
        exact = np.mean([set(r["kept_factors"]) == set(r["active_factors"])
                         for r in sub_doe])
        print(f"\n  screen: {hit:.3f} of active factors recovered, "
              f"{exact:.3f} recovered all 4 exactly")
        print(f"  confirmation outside its own stage-2 region: "
              f"{1 - np.mean([r['inside_stage2'] for r in sub_doe]):.3f}"
              f"   on its boundary: "
              f"{np.mean([r['on_stage2_boundary'] for r in sub_doe]):.3f}")
        op = np.array([r["over_prediction"] for r in sub_doe])
        print(f"  over-prediction at the constrained argmax: median {np.median(op):+.4f}"
              f"   positive in {np.mean(op > 0):.3f} of cells")

        # POST-HOC (Q20 §3). The registered `regret` above is best-so-far over all
        # 48 points. The arm's OUTPUT is the stage-4 recipe, which is never the
        # observed argmax -- so scoring the output instead is the stricter of the
        # two defensible rules, and the gap between them is what the arm's own
        # prediction costs it.
        conf = _per_instance(sub_doe, insts, key="regret_at_confirmation")
        d_ = conf - per["qlogei"]
        m, lo, hi = instance_bootstrap(d_, n_boot=2000)
        try:
            p = wilcoxon(d_).pvalue
        except ValueError:
            p = float("nan")
        print(f"\n  POST-HOC, scored at the arm's OUTPUT (stage-4 recipe) instead:")
        print(f"    mean regret {conf.mean():>8.4f}  (registered scoring: "
              f"{per['doe'].mean():.4f})")
        print(f"    vs   qlogei: {m:>+8.4f}  [{lo:>+8.4f}, {hi:>+8.4f}]  "
              f"wilcoxon p={p:.4f}")


def main() -> None:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"Q27 · d=8 DoE arm · registration must predate this run · HEAD={head}")
    print(f"stage-1 fraction: 2^({DIM}-{STAGE1_FRACTION[DIM]}), "
          f"budget {BUDGET}, {N_INSTANCES} instances x {N_SEEDS} seeds\n")

    ens = load_ensemble(dim=DIM)[:N_INSTANCES]
    stored = _stored()

    print("FIDELITY — the stored d=8 numbers this arm will be compared against:")
    check_fidelity(ens, stored)

    print("\nRUNNING the d=8 DoE arm:")
    rows = run_arm(ens)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1))
    report(rows, stored)
    print(f"\nrows written to {OUT}")


if __name__ == "__main__":
    main()
