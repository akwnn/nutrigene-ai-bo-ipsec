"""Q52 §1.2 — where does the curve flatten? The best arm, one cell, out to 500.

    python scripts/run_q52_flatten.py [n_instances]   # log at results/q52-flatten.log

THE DECISION THIS MAKES
-----------------------
*"If it is flat by 100, no budget reaches the tighter targets and the grid should stop
there."* The cap in the budget-to-target grid is registered as 200 subject to this
check, so the check has to happen first.

ONE LONG RUN, SCORED AT EVERY PREFIX — NOT EIGHT FIXED-BUDGET RUNS
-------------------------------------------------------------------
Budget-to-target asks *"how many evaluations to reach quality T"*, which is a question
about a lab that keeps going until it arrives. It never pre-commits to a budget. So the
faithful instrument is one campaign scored after every evaluation, and that is also 1
run rather than 8. Regret at index n is "what this campaign would have handed you had
it stopped at n" -- exactly the quantity the grid needs.

What this does **not** license: claiming the 48-prefix reproduces E2's 48-point number.
``batch_plan`` gives budget 48 a final partial batch of 2 where a 500-run takes a full
4, so the two traces diverge in their last points before 48. E2's number is quoted
below as a reference point, never as a fidelity gate.

THE CELL, AND WHY THIS ONE
---------------------------
d=6, sigma_rel=0.25 -- the registered primary cell, and the cell where the classical arm
beat BO in E2. Picking the cell where BO already looked strongest would make a
flattening result unfalsifiable.

THE ARM, AND WHY THIS ONE
--------------------------
qLogEI. Q50 settled it: design-averaged at this cell, ``lhs - qlogei = +0.0219``
[+0.0145, +0.0292], p = 1.8e-05, BO ahead on 21 of 25 instances. Before Q50 the "best
arm" at this cell would arguably have been ``lhs``, and the answer here would have been
about a static design.
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

from boec.campaign import Campaign, CampaignConfig      # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.metrics import constrained_argmax             # noqa: E402
from boec.oracles import load_ensemble                  # noqa: E402
from boec.surrogate import build_gp                     # noqa: E402
from boec.torch_oracle import BiphasicOracle            # noqa: E402

DIM, SIGMA, SEED = 6, 0.25, 0
BUDGET = 500
#: Rule A is free at every index; rule C costs a GP fit plus an argmax (~3.5s) each.
CHECKPOINTS = (24, 48, 100, 150, 200, 300, 400, 500)
N_RESTARTS, RAW_SAMPLES = 20, 4096
WORKERS = 4
#: E2's stored qLogEI number at this cell, quoted for orientation only. Q50 showed the
#: design-averaged value is 0.1532; 0.1553 is the single draw E2 happens to sit on.
E2_REFERENCE = 0.1553
RULE = "=" * 96
OUT = ROOT / "results" / "q52-flatten.json"


def _seed_of(instance_id: str, salt: int) -> int:
    return (int(instance_id[:8], 16) * 1000 + salt) % (2**31 - 1)


def one(instance_index: int) -> dict:
    """One 500-evaluation qLogEI campaign, scored at every checkpoint, both rules."""
    t0 = time.time()
    inst = load_ensemble(dim=DIM)[instance_index]
    bounds = torch.stack([torch.zeros(DIM, dtype=torch.double),
                          torch.ones(DIM, dtype=torch.double)])
    orac = BiphasicOracle(inst, sigma_rel=SIGMA, seed=SEED)
    camp = Campaign(orac, bounds, CampaignConfig(d=DIM, budget=BUDGET, q=4, seed=SEED))
    camp.run()

    # Yvar comes from the campaign, NOT from re-evaluating X. The plug-in variance is a
    # function of the *observed* value, so a fresh evaluate() would pair Y[:n] with the
    # variance of a different noise draw -- and would advance the oracle's RNG mid-loop,
    # making the checkpoints depend on how many of them there are.
    X, Y, V = camp.train_X, camp.train_Y, camp.train_Yvar
    if int(X.shape[0]) != BUDGET:
        raise RuntimeError(f"campaign returned {int(X.shape[0])} points, expected "
                           f"{BUDGET}; every checkpoint index would be off")
    truth = orac.truth(X)
    opt = float(inst.optimum_value)
    curve = reported_best_curve(truth, Y)

    rule_a, rule_c, fails = {}, {}, {}
    for n in CHECKPOINTS:
        rule_a[n] = opt - float(curve[n - 1])
        try:
            model = build_gp(X[:n], Y[:n], V[:n], bounds)

            def mean(Z, _m=model):
                with torch.no_grad():
                    return _m.posterior(Z).mean

            x, _, _ = constrained_argmax(mean, bounds, n_restarts=N_RESTARTS,
                                         raw_samples=RAW_SAMPLES,
                                         seed=_seed_of(inst.instance_id, n))
            rule_c[n] = opt - float(orac.truth(x.reshape(1, -1)))
        except Exception as exc:                          # noqa: BLE001 - recorded
            rule_c[n] = float("nan")
            fails[n] = f"{type(exc).__name__}: {exc}"

    secs = round(time.time() - t0, 1)
    print(f"    instance {instance_index:>2} done in {secs:>6.0f}s   "
          f"rule A 48->500: {rule_a[48]:.4f} -> {rule_a[500]:.4f}", flush=True)
    return dict(instance_index=instance_index, instance_id=inst.instance_id,
                secs=secs, rule_a=rule_a, rule_c=rule_c, failures=fails)


def _ci(v) -> tuple[float, float, float]:
    a = np.asarray([x for x in v], dtype=float)
    m, lo, hi = instance_bootstrap(a[~np.isnan(a)], n_boot=4000)
    return float(m), float(lo), float(hi)


def main() -> None:
    n_inst = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"{RULE}\nQ52 §1.2 — does the best arm's curve flatten? "
          f"qLogEI, d={DIM} sigma={SIGMA}, to {BUDGET}.\n{RULE}")
    print(f"  {n_inst} instances, one campaign each, scored at every prefix.\n")

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {r["instance_index"] for r in done}
    todo = [i for i in range(n_inst) if i not in have]
    if have:
        print(f"  resuming — {len(have)} instances already on disk\n")

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for row in pool.map(one, todo):
            done.append(row)
            OUT.write_text(json.dumps(dict(budget=BUDGET, dim=DIM, sigma=SIGMA,
                                           checkpoints=list(CHECKPOINTS),
                                           rows=done), indent=1))

    rows = sorted(done, key=lambda r: r["instance_index"])[:n_inst]
    print(f"\n  n = {len(rows)} instances, qLogEI, d={DIM} sigma_rel={SIGMA}")
    print(f"    {'budget':>7}{'rule A (reported best)':>30}"
          f"{'rule C (posterior mean)':>30}")
    prev_a = None
    for n in CHECKPOINTS:
        am, alo, ahi = _ci([r["rule_a"][str(n)] if str(n) in r["rule_a"]
                            else r["rule_a"][n] for r in rows])
        cm, clo, chi = _ci([r["rule_c"][str(n)] if str(n) in r["rule_c"]
                            else r["rule_c"][n] for r in rows])
        delta = "" if prev_a is None else f"  ({am - prev_a:+.4f})"
        prev_a = am
        print(f"    {n:>7}   {am:>7.4f} [{alo:>6.4f},{ahi:>6.4f}]{delta:>10}"
              f"   {cm:>7.4f} [{clo:>6.4f},{chi:>6.4f}]")
    print(f"\n  E2's stored qLogEI at this cell, for orientation: {E2_REFERENCE:.4f} "
          f"at n=48 (single design draw; Q50's design-averaged value is 0.1532).")

    # the flattening verdict, paired at instance level
    print(f"\n{RULE}\n  IS IT FLAT BY 100?  Paired contrasts against n=100.\n{RULE}")
    for rule in ("rule_a", "rule_c"):
        base = np.array([r[rule].get(str(100), r[rule].get(100)) for r in rows],
                        dtype=float)
        print(f"\n  {rule.replace('_', ' ').upper()}")
        for n in (200, 300, 500):
            later = np.array([r[rule].get(str(n), r[rule].get(n)) for r in rows],
                             dtype=float)
            d = base - later                       # positive => the larger budget helps
            ok = ~np.isnan(d)
            m, lo, hi = instance_bootstrap(d[ok], n_boot=4000)
            verdict = ("helps" if lo > 0 else "hurts" if hi < 0 else
                       "flat — CI covers zero")
            print(f"    100 -> {n:>3}: {m:>+8.4f} [{lo:>+7.4f},{hi:>+7.4f}]  {verdict}")

    print(f"\n  -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
