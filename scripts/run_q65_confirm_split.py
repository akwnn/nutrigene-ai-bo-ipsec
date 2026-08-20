"""Q65 — budget-neutral explore/confirm split for BO. PILOT, exploratory.

    python scripts/run_q65_confirm_split.py --workers 4
    python scripts/run_q65_confirm_split.py --splits 48,44,40,36 --cells 6:0.25

WHAT THIS ASKS
--------------
Q57 decomposes the primary-cell gap: DoE/RSM measured-value argmax 0.0958 against
qLogNEI 0.1532. Search explains little of it. Identification explains most:

    arm        measured   search    identification gap
    DoE/RSM     0.0958    0.0597    0.0361
    qLogEI      0.1553    0.0755    0.0797
    qLogNEI     0.1532    0.0834    0.0698

BO's identification gap is 2.2x the classical arm's at sigma=0.25 and roughly equal at
sigma=0.10, which points at noise rather than at BO in general. The mechanism is already
stated in the paper: BO clusters near the optimum, so a single noisy reading cannot
separate its own near-ties, while the CCD spreads out and its winner stands above noise.

So: spend part of the SAME 48-well budget re-measuring a shortlist instead of visiting
new wells. Averaging repeat readings attacks identification directly, which is the only
term with enough headroom to matter.

WHY THIS IS NOT TABLE 4's TOP-3 CONFIRMATION
--------------------------------------------
Table 4 spends **+3 extra wells** on confirmation, so that arm ran a 51-well campaign
against a 48-well competitor. Here the confirmation wells come **out of** the 48. The
budget stays matched, which is the whole point of the comparison, and the trade is
therefore real: every confirmation well is a well not spent exploring.

HEADROOM, AND THE BAR
---------------------
Perfect identification would put qLogEI at its search value, 0.0755, against 0.0958 --
a BO win of +0.0203. So a win is arithmetically available. But matching the classical
arm's identification is NOT enough: BO must get its gap below 0.0203 while DoE sits at
0.0361, because BO also searches slightly worse. Roughly 44% better than DoE to win
outright; roughly halving its own gap to reach equivalence within the 0.02 SESOI.

STATUS: EXPLORATORY. NOT A REGISTERED RESULT.
---------------------------------------------
n=25 gives MDE ~0.027, larger than the 0.02 SESOI, so this cannot declare equivalence
and must not be quoted as if it could. It sizes an effect and answers one go/no-go:
is the 0.0698--0.0797 identification gap closable enough to justify the registered
version at n=100 with a matched classical replication arm (spec
`docs/superpowers/specs/2026-08-20-bo-steelman-design.md`, arms B1 and C1)?

**A BO-only upgrade is not a result.** The project's fairness rule (`START-HERE-PERSON-A.md`
Q5) forbids tuning one arm while the baseline keeps defaults. C1 -- a classical arm that
also replicates -- is required before any of this reaches the paper.

THE GATE, AND WHY IT IS ON THE CLASSICAL ARM
-------------------------------------------
The DoE arm is gated bit-exactly against Q57's stored `doe_rule_a`. It replays at
delta 0.0 because it never touches the acquisition optimizer.

**The BO arm is deliberately NOT gated against stored values, and cannot be.** Stored BO
results are not reproducible from code and seed: BoTorch's acquisition retry depended on
whether a warning had already fired in that worker process, and these runs were sharded
across processes with `warnings.filterwarnings("ignore")`. Replaying Q57 at its own
commit (a189ddd), with its own loop order and a byte-identical environment, gives some
rows bit-exact and others off by up to 1.2e-01 -- the signature of a branch taken
differently, not of drift. The fix now in `campaign.ask()` reseeds from recorded campaign
state and makes future runs replayable; it also means stored numbers can only be
re-generated, never reproduced.

So the BO baseline here is **this run's own 48/0 split**, executed under identical code in
the same job set. That comparison is internally valid regardless of the stored numbers.
The stored 0.1532 is printed alongside as a diagnostic only, never as a gate.
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

from boec.campaign import Campaign, CampaignConfig                    # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.selection import top_k_average                              # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402

BUDGET = 48
Q = 4
ACQ = "qlognei"
N_INSTANCES = 25
N_SEEDS = 2
DOE_GATE_TOL = 0.0
Q57 = ROOT / "results" / "q57-search-vs-id.json"
OUT = ROOT / "results" / "q65-confirm-split.json"


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _pooled_deep(y: torch.Tensor, reads: dict[int, list[float]]) -> int:
    """Argmax of the pooled mean of every reading of each shortlisted well.

    PILOT-LOCAL. ``top_k_average`` is the shared one-read-each rule and is imported,
    not reimplemented. This many-reads-each variant has no shared implementation yet;
    if it is promoted past the pilot it belongs in ``boec.selection``, not here.
    """
    best_i, best_v = -1, -np.inf
    for i, extra in reads.items():
        pooled = (float(y[i]) + sum(extra)) / (1 + len(extra))
        if pooled > best_v:
            best_i, best_v = i, pooled
    return best_i


def one(job: tuple[int, float, int, int, int]) -> list[dict]:
    """One (instance, seed) at one cell and one split. Returns a row per rule."""
    dim, sigma, idx, seed, n_explore = job
    t0 = time.time()
    n_confirm = BUDGET - n_explore
    inst = load_ensemble(dim=dim)[idx]
    opt = float(inst.optimum_value)

    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    camp = Campaign(o, _bounds(dim),
                    CampaignConfig(d=dim, budget=n_explore, q=Q, seed=seed,
                                   acq=AcqConfig(kind=ACQ))).run()

    X, Y = camp.train_X, camp.train_Y
    truth = o.truth(X)
    t = truth.double().reshape(-1)
    y = Y.double().reshape(-1)

    # Search is a property of the visited set alone: no locating to do.
    search = opt - float(t.max())
    # The no-confirmation locator, on however many wells exploration bought.
    measured = opt - float(reported_best_curve(truth, Y)[-1])

    base = dict(dim=dim, sigma=sigma, instance=inst.instance_id, instance_index=idx,
                seed=seed, n_explore=n_explore, n_confirm=n_confirm,
                search=search, measured_explore_only=measured,
                secs=round(time.time() - t0, 1))

    if n_confirm == 0:
        return [dict(base, rule="measured_argmax", wells_used=n_explore,
                     regret=measured, id_gap=measured - search)]

    rows = []

    # --- wide: shortlist n_confirm wells, one extra reading each -----------------
    k = n_confirm
    shortlist = torch.topk(y, k).indices
    conf = y.clone()
    conf[shortlist] = o.observe(X[shortlist])[0].double().reshape(-1)
    i_wide = top_k_average(Y, conf.reshape(-1, 1), k=k)
    rows.append(dict(base, rule="wide", wells_used=n_explore + k,
                     regret=opt - float(t[i_wide]),
                     id_gap=(opt - float(t[i_wide])) - search))

    # --- deep: 3 candidates, the confirmation budget split between them ----------
    if n_confirm >= 3:
        k_deep = 3
        cand = torch.topk(y, k_deep).indices
        per = n_confirm // k_deep
        left = n_confirm - per * k_deep          # remainder goes to the leader
        reads: dict[int, list[float]] = {}
        used = 0
        for rank, i in enumerate(cand.tolist()):
            r = per + (left if rank == 0 else 0)
            reads[i] = [float(v) for v in
                        o.observe(X[i].repeat(r, 1))[0].double().reshape(-1)] if r else []
            used += r
        i_deep = _pooled_deep(y, reads)
        rows.append(dict(base, rule="deep", wells_used=n_explore + used,
                         regret=opt - float(t[i_deep]),
                         id_gap=(opt - float(t[i_deep])) - search))
    return rows


def doe_one(job: tuple[int, float, int, int]) -> dict:
    """The classical comparator, regenerated in-run. Gated bit-exactly against Q57."""
    dim, sigma, idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=dim)[idx]
    opt = float(inst.optimum_value)
    od = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    r = run_doe_arm(od, _bounds(dim), truth=od.truth, budget=BUDGET, seed=seed)
    truth = od.truth(r.X_visited)
    measured = opt - float(reported_best_curve(truth, r.Y_visited)[-1])
    search = opt - float(truth.double().reshape(-1).max())
    return dict(dim=dim, sigma=sigma, instance=inst.instance_id, instance_index=idx,
                seed=seed, n_explore=BUDGET, n_confirm=0, rule="doe_measured",
                wells_used=BUDGET, regret=measured, search=search,
                id_gap=measured - search, measured_explore_only=measured,
                secs=round(time.time() - t0, 1))


def _gate(rows: list[dict]) -> dict:
    """Bit-exact gate on the DoE arm. BO is not gated -- see the module docstring."""
    if not Q57.exists():
        raise SystemExit(f"gate reference missing: {Q57}")
    stored = {(r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4)):
              r for r in json.loads(Q57.read_text())["rows"]}
    worst, checked = 0.0, 0
    for r in rows:
        if r["rule"] != "doe_measured":
            continue
        key = (r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4))
        if key not in stored:
            continue
        worst = max(worst, abs(r["regret"] - stored[key]["doe_rule_a"]))
        checked += 1
    if checked < 4:
        raise SystemExit(f"DoE gate checked only {checked} rows; that is not coverage")
    if worst > DOE_GATE_TOL:
        raise SystemExit(
            f"DoE arm does not reproduce Q57: worst |delta| = {worst:.3e} > "
            f"{DOE_GATE_TOL:.0e}. The comparator is not faithful; stop.")

    # BO drift vs stored: recorded as a diagnostic, never a pass/fail.
    bo_worst, bo_checked = 0.0, 0
    for r in rows:
        if r["rule"] != "measured_argmax":
            continue
        key = (r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4))
        if key in stored:
            bo_worst = max(bo_worst, abs(r["regret"] - stored[key]["nei_rule_a"]))
            bo_checked += 1
    return dict(doe_rows_checked=checked, doe_worst_abs_delta=worst, doe_tol=DOE_GATE_TOL,
                bo_rows_compared=bo_checked, bo_worst_abs_delta_vs_stored=bo_worst,
                bo_note=("NOT a gate. Stored BO is not reproducible from code+seed "
                         "(acquisition retry depended on per-process warning state). "
                         "The in-run 48/0 split is the BO baseline."),
                reference=str(Q57.relative_to(ROOT)))


def summarize(rows: list[dict]) -> list[dict]:
    """Seeds averaged per landscape first, so n is landscapes, not runs."""
    out = []
    cells = sorted({(r["dim"], r["sigma"]) for r in rows})
    for dim, sigma in cells:
        for n_explore in sorted({r["n_explore"] for r in rows}, reverse=True):
            for rule in ("doe_measured", "measured_argmax", "wide", "deep"):
                sel = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma
                       and r["n_explore"] == n_explore and r["rule"] == rule]
                if not sel:
                    continue
                by: dict[str, list[dict]] = {}
                for r in sel:
                    by.setdefault(r["instance"], []).append(r)
                reg = np.array([np.mean([x["regret"] for x in v]) for v in by.values()])
                srch = np.array([np.mean([x["search"] for x in v]) for v in by.values()])
                m, lo, hi = instance_bootstrap(reg)
                gm, glo, ghi = instance_bootstrap(reg - srch)
                out.append(dict(
                    dim=dim, sigma=sigma, n_explore=n_explore,
                    n_confirm=BUDGET - n_explore, rule=rule, n=len(by),
                    mean_regret=float(m), regret_lo=float(lo), regret_hi=float(hi),
                    mean_search=float(srch.mean()),
                    mean_id_gap=float(gm), id_gap_lo=float(glo), id_gap_hi=float(ghi),
                ))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--splits", default="48,44,40,36")
    p.add_argument("--cells", default="6:0.25")
    a = p.parse_args()

    splits = [int(s) for s in a.splits.split(",")]
    cells = [(int(c.split(":")[0]), float(c.split(":")[1])) for c in a.cells.split(",")]
    jobs = [(d, s, i, sd, ne) for d, s in cells for ne in splits
            for i in range(N_INSTANCES) for sd in range(N_SEEDS)]
    doe_jobs = [(d, s, i, sd) for d, s in cells
                for i in range(N_INSTANCES) for sd in range(N_SEEDS)]
    print(f"Q65 PILOT (exploratory) — {len(jobs)} campaigns, {a.workers} workers")
    print(f"  cells {cells}  splits {splits}  acq {ACQ}\n")

    rows: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        futs |= {ex.submit(doe_one, j): j for j in doe_jobs}
        total = len(jobs) + len(doe_jobs)
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            rows.extend(r if isinstance(r, list) else [r])
            if n % 20 == 0 or n == total:
                print(f"  {n}/{total}  {time.time()-t0:.0f}s", flush=True)

    gate = _gate(rows)
    print(f"\nDoE gate OK: {gate['doe_rows_checked']} rows bit-exact vs Q57 "
          f"(worst {gate['doe_worst_abs_delta']:.3e})")
    print(f"BO vs stored (diagnostic only): worst {gate['bo_worst_abs_delta_vs_stored']:.3e} "
          f"over {gate['bo_rows_compared']} rows\n")

    summary = summarize(rows)
    OUT.write_text(json.dumps(dict(
        ticket="Q65", status="EXPLORATORY PILOT — not a registered result",
        note=("Budget-neutral explore/confirm split for qLogNEI. Confirmation wells come "
              "OUT of the 48, unlike Table 4's +3. n=25 (MDE ~0.027 > SESOI 0.02): sizes "
              "an effect, cannot declare equivalence. Needs matched classical "
              "replication arm (C1) before any paper use."),
        budget=BUDGET, acq=ACQ, q=Q,
        provenance=dict(
            git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
            argv=sys.argv, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            torch=torch.__version__, numpy=np.__version__),
        gate=gate, summary=summary, rows=rows), indent=1) + "\n")
    print(f"wrote {OUT}\n")

    ref = {"6:0.25": dict(doe=0.0958, nei=0.1532, nei_search=0.0834)}
    for s in summary:
        key = f"{s['dim']}:{s['sigma']}"
        r = ref.get(key)
        tag = ""
        if r:
            tag = f"   vs DoE {r['doe']:.4f} -> {s['mean_regret'] - r['doe']:+.4f}"
        print(f"  {s['n_explore']:>2}/{s['n_confirm']:<2} {s['rule']:<16} "
              f"regret {s['mean_regret']:.4f} [{s['regret_lo']:.4f},{s['regret_hi']:.4f}]  "
              f"search {s['mean_search']:.4f}  id_gap {s['mean_id_gap']:.4f}{tag}")


if __name__ == "__main__":
    main()
