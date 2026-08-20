"""Q71 — regenerate the two headline tables under the fixed acquisition seeding (G21).

    python scripts/run_q71_regenerate_headline.py --workers 6

WHY
---
Every BO number in Tables 1 and 2 was produced before `Campaign.ask()` reseeded from
recorded campaign state. Those stored values cannot be reproduced from code and seed:
BoTorch's acquisition retry depended on whether a warning had already fired in that worker
process, and the runs were sharded with warnings suppressed. Replaying the committed file at
its own commit, in a byte-identical environment, returns some rows bit-exact and others
different by up to 1.2e-01. Full diagnosis in G21.

This run regenerates both tables under the fixed path, on the SAME committed 25-landscape
ensemble and the same design, so the only thing that changes is the defect. It does not
extend n and it does not alter any arm's policy.

**Expect the numbers to move.** That is the point. Post-fix values are not corrections of
arithmetic errors -- the old ones were correct for the trajectories that were actually run.
They are a different, reproducible draw. Report them as a regeneration, never silently
beside pre-fix values.

WHAT IS REGENERATED
-------------------
Four cells (d in {6,8} x sigma in {0.25,0.10}), four arms, two locators:

    arms      DoE/RSM, qLogEI, qLogNEI, random
    Table 1   measured-value argmax  -- pick the largest noisy reading, score its truth
    Table 2   hidden tested-best     -- best TRUE value among visited wells (search only)
              identification share   -- (measured contrast - search contrast) / measured

GATE
----
The DoE arm must reproduce Q57's stored `doe_rule_a` BIT-EXACTLY in all four cells. The
classical arm never touches the acquisition optimizer, so it is unaffected by G21 and must
still replay at delta 0.0. If it does not, the harness is wrong rather than the defect, and
the run stops. The BO arms are deliberately ungated -- there is nothing trustworthy to gate
them against, which is the whole reason this run exists.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
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

from boec.campaign import Campaign, CampaignConfig                    # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.optimizers import AcqConfig, random_design                  # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402

BUDGET, Q = 48, 4
N_INSTANCES, N_SEEDS = 25, 2
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
Q57 = ROOT / "results" / "q57-search-vs-id.json"
OUT = ROOT / "results" / "q71-headline-regenerated.json"


def _bounds(d):
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _score(truth, Y, opt):
    """(measured-value argmax regret, hidden tested-best regret)."""
    t = truth.double().reshape(-1)
    return opt - float(reported_best_curve(truth, Y)[-1]), opt - float(t.max())


def one(job):
    dim, sigma, idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=dim)[idx]
    opt = float(inst.optimum_value)
    bounds = _bounds(dim)
    row = dict(dim=dim, sigma=sigma, instance=inst.instance_id, instance_index=idx, seed=seed)

    for tag, kind in (("qlogei", "qlogei"), ("qlognei", "qlognei")):
        o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        c = Campaign(o, bounds, CampaignConfig(d=dim, budget=BUDGET, q=Q, seed=seed,
                                               acq=AcqConfig(kind=kind))).run()
        m, s = _score(o.truth(c.train_X), c.train_Y, opt)
        row[f"{tag}_measured"], row[f"{tag}_search"] = m, s

    od = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    r = run_doe_arm(od, bounds, truth=od.truth, budget=BUDGET, seed=seed)
    m, s = _score(od.truth(r.X_visited), r.Y_visited, opt)
    row["doe_measured"], row["doe_search"] = m, s

    orr = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    Xr = random_design(bounds, BUDGET, seed=seed)
    Yr, _ = orr.observe(Xr)
    m, s = _score(orr.truth(Xr), Yr, opt)
    row["random_measured"], row["random_search"] = m, s

    row["secs"] = round(time.time() - t0, 1)
    return row


def _gate(rows):
    stored = {(r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4)): r["doe_rule_a"]
              for r in json.loads(Q57.read_text())["rows"]}
    worst, checked = 0.0, 0
    for r in rows:
        k = (r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4))
        if k in stored:
            worst = max(worst, abs(r["doe_measured"] - stored[k])); checked += 1
    if checked < 100:
        raise SystemExit(f"DoE gate covered only {checked} rows; expected 200")
    if worst != 0.0:
        raise SystemExit(
            f"DoE arm no longer reproduces Q57 (worst {worst:.3e}). The classical arm is not "
            "affected by G21, so this means the harness is wrong. Stop.")
    return dict(doe_rows_checked=checked, doe_worst_abs_delta=worst,
                bo_note="BO arms intentionally ungated: stored BO is not reproducible.")


def _per(rows, key):
    by = {}
    for r in rows:
        by.setdefault(r["instance"], []).append(r[key])
    return np.array([np.mean(v) for _, v in sorted(by.items())])


def summarize(rows):
    out = []
    for dim, sigma in CELLS:
        sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-9]
        if not sub:
            continue
        cell = dict(dim=dim, sigma=sigma, n=len({r["instance"] for r in sub}), arms={}, contrasts=[])
        for arm in ("doe", "qlogei", "qlognei", "random"):
            cell["arms"][arm] = dict(
                measured=float(_per(sub, f"{arm}_measured").mean()),
                search=float(_per(sub, f"{arm}_search").mean()))
        doe_m, doe_s = _per(sub, "doe_measured"), _per(sub, "doe_search")
        for arm in ("qlogei", "qlognei"):
            bo_m, bo_s = _per(sub, f"{arm}_measured"), _per(sub, f"{arm}_search")
            dm, dlo, dhi = instance_bootstrap(doe_m - bo_m)
            sm, slo, shi = instance_bootstrap(doe_s - bo_s)
            share = float(1 - sm / dm) if abs(dm) > 1e-12 else None
            cell["contrasts"].append(dict(
                arm=arm,
                measured=dict(mean=float(dm), lo=float(dlo), hi=float(dhi),
                              wilcoxon_p=float(wilcoxon(doe_m - bo_m).pvalue)),
                search=dict(mean=float(sm), lo=float(slo), hi=float(shi),
                            wilcoxon_p=float(wilcoxon(doe_s - bo_s).pvalue)),
                identification_share=share))
        out.append(cell)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    jobs = [(d, s, i, sd) for d, s in CELLS
            for i in range(N_INSTANCES) for sd in range(N_SEEDS)]
    print(f"Q71 — regenerating Tables 1 and 2 post-fix. {len(jobs)} rows, "
          f"{len(jobs)*2} BO campaigns.\n")
    rows, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for k, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if k % 25 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    gate = _gate(rows)
    print(f"\nDoE gate OK: {gate['doe_rows_checked']} rows bit-exact vs Q57\n")
    summary = summarize(rows)
    OUT.write_text(json.dumps(dict(
        ticket="Q71",
        status="POST-FIX REGENERATION of Tables 1 and 2. Not comparable row-for-row with "
               "stored pre-fix values; see G21.",
        config=dict(budget=BUDGET, q=Q, n_instances=N_INSTANCES, seeds=N_SEEDS, cells=CELLS),
        provenance=dict(git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                        capture_output=True, text=True).stdout.strip(),
                        argv=sys.argv, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        gate=gate, summary=summary, rows=rows), indent=1) + "\n")
    print(f"wrote {OUT}\n")
    for c in summary:
        a_ = c["arms"]
        print(f"--- d={c['dim']} sigma={c['sigma']}  (n={c['n']})")
        print(f"    measured: DoE {a_['doe']['measured']:.4f}  qLogEI {a_['qlogei']['measured']:.4f}  "
              f"qLogNEI {a_['qlognei']['measured']:.4f}  random {a_['random']['measured']:.4f}")
        print(f"    search:   DoE {a_['doe']['search']:.4f}  qLogEI {a_['qlogei']['search']:.4f}  "
              f"qLogNEI {a_['qlognei']['search']:.4f}")
        for ct in c["contrasts"]:
            sh = "—" if ct["identification_share"] is None else f"{ct['identification_share']:.0%}"
            print(f"    DoE-{ct['arm']:<8} measured {ct['measured']['mean']:+.4f} "
                  f"[{ct['measured']['lo']:+.4f},{ct['measured']['hi']:+.4f}]  "
                  f"search {ct['search']['mean']:+.4f} "
                  f"[{ct['search']['lo']:+.4f},{ct['search']['hi']:+.4f}]  id share {sh}")
        print()


if __name__ == "__main__":
    main()
