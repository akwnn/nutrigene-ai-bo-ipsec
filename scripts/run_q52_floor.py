"""Q52 §1.1 — the identification floor. Which budget-to-target targets are reachable?

    python scripts/run_q52_floor.py            # log at results/q52-floor.log

THE DECISION THIS MAKES
-----------------------
The budget-to-target brief registers eight targets, 0.30 down to 0.05, and instructs:
*"If a target sits below that floor, drop it from the grid and record why."* This
computes the floor so that pruning happens **before** the grid runs and is not a
post-hoc choice made after seeing which targets flattered which arm.

THE CONSTRUCTION — an oracle-search lower bound
------------------------------------------------
Plant the true optimum in the visited set and score normally. A method that has already
visited the best point in the space cannot be beaten by one that still has to find it,
so the surviving regret is pure **identification** error and bounds every arm below.
It is deliberately loose -- real arms must also search -- because a loose lower bound
still prunes: a target under the floor is unreachable for certain.

WHY THE TWO RULES GET SEPARATE FLOORS
--------------------------------------
They move in opposite directions, so a single number would be wrong for one of them.

* **Rule A (best-observed, the registered rule)** picks by observation. Every extra
  point is another chance for a mediocre one to draw lucky noise and displace the
  planted optimum, so its floor **rises with n**. The best reachable target under rule
  A is therefore not at the cap -- it is at some interior budget, and past that,
  spending more makes the reportable answer worse.
* **Rule C (posterior mean)** pools everything into one fit, so its floor **falls with
  n**, limited by estimation rather than by the luckiest draw.

WHAT IS NOT MEASURED HERE
--------------------------
Rule C's floor uses the production GP on a design that is space-filling plus one
planted point. A real arm's design is chosen adaptively and is not space-filling, so
rule C's number is a floor for *this* design family, not for every conceivable one.
Stated rather than buried: it is the weaker of the two bounds.
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.diagnostics import instance_bootstrap          # noqa: E402
from boec.floor import planted_design, rule_a_floor      # noqa: E402
from boec.metrics import constrained_argmax              # noqa: E402
from boec.oracles import load_ensemble                   # noqa: E402
from boec.surrogate import build_gp                      # noqa: E402
from boec.torch_oracle import BiphasicOracle             # noqa: E402

#: The eight targets the brief registers, denser at the tight end.
TARGETS = (0.30, 0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05)

N_INSTANCES = 25
NS = (24, 48, 96, 192, 384)
SIGMAS = (0.10, 0.25)
DIMS = (6, 8)
SIGMA_ADD = 0.01

#: Rule A needs no model, so precision comes from noise draws rather than instances.
N_REPS_A = 400
#: Rule C fits a GP per draw at ~3.5s, so it buys precision far more slowly.
N_REPS_C = 5

N_RESTARTS, RAW_SAMPLES = 20, 4096
WORKERS = 4
RULE = "=" * 104


def _seed_of(instance_id: str, salt: int) -> int:
    return (int(instance_id[:8], 16) * 1000 + salt) % (2**31 - 1)


def _rule_c_once(X, orac, bounds, opt, seed) -> float:
    """Regret at the posterior-mean argmax of a GP fitted to one noisy readout."""
    Y, V = orac.evaluate(X)
    model = build_gp(X, Y, V, bounds)

    def mean(Z):
        with torch.no_grad():
            return model.posterior(Z).mean

    x, _, _ = constrained_argmax(mean, bounds, n_restarts=N_RESTARTS,
                                 raw_samples=RAW_SAMPLES, seed=seed)
    return float(opt) - float(orac.truth(x.reshape(1, -1)))


def cell(task: tuple[int, float, int]) -> dict:
    """One (dim, sigma, n). Returns per-instance floors under both rules."""
    dim, sigma, n = task
    t0 = time.time()
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    a_reg, a_hit, c_reg = [], [], []

    for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
        opt = float(inst.optimum_value)
        x_star = torch.as_tensor(inst.optimum_x, dtype=torch.double)
        X = planted_design(bounds, n, x_star, seed=_seed_of(inst.instance_id, 2))

        # Rule A: the truth at the visited points is fixed, only the assay resamples.
        truth = BiphasicOracle(inst, sigma_rel=sigma,
                               seed=0).truth(X).numpy().ravel()
        f = rule_a_floor(truth, optimum_value=opt, sigma_rel=sigma,
                         sigma_add=SIGMA_ADD, n_reps=N_REPS_A,
                         seed=_seed_of(inst.instance_id, 3))
        a_reg.append(f.mean_regret)
        a_hit.append(f.hit_rate)

        # Rule C: a fresh readout and a fresh fit per rep.
        reps = []
        for r in range(N_REPS_C):
            orac = BiphasicOracle(inst, sigma_rel=sigma, seed=r)
            try:
                reps.append(_rule_c_once(X, orac, bounds, opt,
                                         _seed_of(inst.instance_id, 4 + r)))
            except Exception as exc:                      # noqa: BLE001 - recorded
                reps.append(float("nan"))
                print(f"    rule C failed at d={dim} s={sigma} n={n}: "
                      f"{type(exc).__name__}: {exc}", flush=True)
        c_reg.append(float(np.nanmean(reps)))

    return dict(dim=dim, sigma=sigma, n=n, secs=round(time.time() - t0, 1),
                rule_a=a_reg, rule_c=c_reg, hit_rate=a_hit)


def _ci(v: list[float]) -> tuple[float, float, float]:
    m, lo, hi = instance_bootstrap(np.asarray(v, dtype=float), n_boot=4000)
    return float(m), float(lo), float(hi)


def main() -> None:
    tasks = [(d, s, n) for d in DIMS for s in SIGMAS for n in NS]
    print(f"{RULE}\nQ52 §1.1 — the identification floor. Plant the optimum, then see "
          f"whether the assay can name it.\n{RULE}")
    print(f"  {len(tasks)} cells, {N_INSTANCES} instances, "
          f"{N_REPS_A} noise draws for rule A and {N_REPS_C} for rule C\n")

    if WORKERS == 1:                 # in-process, so a smoke run can patch the globals
        rows = [cell(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=WORKERS) as pool:
            rows = list(pool.map(cell, tasks))
    out = {(r["dim"], r["sigma"], r["n"]): r for r in rows}

    for dim in DIMS:
        for sigma in SIGMAS:
            print(f"\n  d={dim}  sigma_rel={sigma}")
            print(f"    {'n':>6}{'rule A floor':>28}{'hit rate':>10}"
                  f"{'rule C floor':>28}")
            for n in NS:
                r = out[(dim, sigma, n)]
                am, alo, ahi = _ci(r["rule_a"])
                cm, clo, chi = _ci(r["rule_c"])
                print(f"    {n:>6}   {am:>7.4f} [{alo:>6.4f},{ahi:>6.4f}]"
                      f"{100 * float(np.mean(r['hit_rate'])):>9.0f}%"
                      f"   {cm:>7.4f} [{clo:>6.4f},{chi:>6.4f}]")
            def _best(rule, _d=dim, _s=sigma):
                n = min(NS, key=lambda k: float(np.mean(out[(_d, _s, k)][rule])))
                return float(np.mean(out[(_d, _s, n)][rule])), n

            (ba, na), (bc, nc) = _best("rule_a"), _best("rule_c")
            print(f"    best reachable: rule A {ba:.4f} at n={na}"
                  f"   |   rule C {bc:.4f} at n={nc}")

    # ---------------------------------------------------------------- the pruning
    print(f"\n{RULE}\n  TARGET PRUNING — a target below the floor cannot be reached by "
          f"any arm at any budget\n  in the cap, because the floor already assumes the "
          f"optimum was visited.\n{RULE}")
    print("  A target is KEPT if some (cell, rule) can reach it. Dropping a target that")
    print("  only sigma=0.10 can reach would delete the noise contrast of §3.4, which is")
    print("  the headline of the experiment — 'reachable if you halve your assay CV' is")
    print("  the finding, not a nuisance. Targets unreachable everywhere measure only")
    print("  the cap, and those are the ones that go.\n")

    cells = [(d, s) for d in DIMS for s in SIGMAS]
    floors = {(d, s, rule): min(float(np.mean(out[(d, s, n)][rule])) for n in NS)
              for d, s in cells for rule in ("rule_a", "rule_c")}

    for rule in ("rule_a", "rule_c"):
        print(f"  under {rule.replace('_', ' ').upper()}:")
        print(f"    {'target':>8}" + "".join(f"{f'd={d} s={s}':>13}" for d, s in cells))
        for t in TARGETS:
            print(f"    {t:>8.2f}" + "".join(
                f"{'reachable' if t > floors[(d, s, rule)] else 'CENSORED':>13}"
                for d, s in cells))
        print()

    reach = {t: [(d, s, r) for d, s in cells for r in ("rule_a", "rule_c")
                 if t > floors[(d, s, r)]] for t in TARGETS}
    survivors = [t for t in TARGETS if reach[t]]
    dropped = [t for t in TARGETS if not reach[t]]

    print(f"  REGISTERED GRID becomes {survivors}")
    if dropped:
        print(f"  DROPPED {dropped} — below the identification floor in every cell "
              f"under both\n  rules, so no arm can reach them and the column would be "
              f"100% censored by construction.")
    else:
        print("  DROPPED none — every registered target is reachable in at least one "
              "(cell, rule).")
    thin = [t for t in survivors if len(reach[t]) <= 2]
    if thin:
        print(f"  Reachable in only one or two of {2 * len(cells)} (cell, rule) "
              f"combinations, so expect heavy censoring: {thin}")

    (ROOT / "results" / "q52-floor.json").write_text(json.dumps(
        dict(targets=list(TARGETS), ns=list(NS), n_reps_a=N_REPS_A,
             n_reps_c=N_REPS_C, n_instances=N_INSTANCES, rows=rows,
             floors={f"d{d}-s{s}-{r}": v for (d, s, r), v in floors.items()},
             survivors=survivors, dropped=dropped), indent=1))
    print(f"\n  -> results/q52-floor.json")


if __name__ == "__main__":
    main()
