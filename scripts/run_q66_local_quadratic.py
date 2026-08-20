"""Q66 / B3 — a local quadratic readout on BO's own wells. PILOT, exploratory.

    python scripts/run_q66_local_quadratic.py --workers 6

WHY THIS RULE AND NOT ANOTHER
-----------------------------
Q65 established the constraint. Spending wells on confirmation improves identification
monotonically (0.0748 -> 0.0630) but degrades search in lockstep (0.0804 -> 0.0965); the
net change at the best split was 0.0023, a tenth of the 0.02 SESOI. **An intervention that
costs wells is cancelled by the search it gives up. Only a free intervention can close the
identification gap.**

This is free. It changes nothing about where BO samples. It re-reads the wells BO already
ran, with the classical arm's own machinery: pool many noisy neighbours into a fitted
surface instead of trusting one reading.

ON FAIRNESS
-----------
The project's rule (`START-HERE-PERSON-A.md` Q5) forbids upgrading one arm while the
baseline keeps defaults. This rule does not upgrade BO past the classical arm -- it gives
BO the readout the classical arm has had all along. The classical arm already fits a
quadratic and takes its constrained argmax; BO has only ever been allowed a single noisy
reading or a GP posterior mean. Equalising a readout is not tuning. Stated here so the
argument is on record before the number is known.

THE PROCEDURE, PER FINISHED 48-WELL qLogNEI CAMPAIGN
---------------------------------------------------
1. Incumbent = visited well with the highest GP posterior mean (`posterior_mean_at_visited`),
   not the highest reading: the starting point should already be noise-pooled.
2. Active dimensions = the ``M_ACTIVE`` factors with the SHORTEST ARD lengthscales in the
   campaign's own fitted GP. This mirrors the classical arm's 6->4 screen, but pays no
   wells for it -- the information is already in the surrogate. The classical arm spends
   20 wells on its screen.
3. Neighbourhood = the ``K_LOCAL`` visited wells nearest the incumbent in the active
   subspace. A full quadratic in m=4 needs 15 terms, so K_LOCAL=24 leaves 9 residual df.
4. Fit a second-order surface on those wells in the active dims; inactive dims are pinned
   at the incumbent's coordinates.
5. Maximise it over the neighbourhood's own bounding box -- IN-REGION by construction.
   Q35 showed what unconstrained quadratic maximisation does: 200/200 saddles, regret
   +0.2995. That failure mode is not being reintroduced in miniature.
6. Score truth at the nominated point.

REGISTERED PREDICTION, BEFORE THE RUN
-------------------------------------
Direction: a modest improvement over measured-value argmax, because 24 pooled readings
beat 1. Magnitude: **smaller than the 0.0594 gap to the classical arm.** It would be a
surprise if this closes it, and that surprise should be treated as suspicious rather than
as a win.

The failure mode is specific and is measured, not assumed: a quadratic fitted to
adaptively-clustered points is poorly conditioned, and its argmax can be driven to the
local box boundary -- the Q35 saddle failure at small scale. Three diagnostics are
recorded per row and reported whatever they say:
  * ``saddle``          - stationary point is not a maximum
  * ``on_boundary``     - the nominated point sits on the local box edge
  * ``fit_failed``      - rank deficiency; recorded as a rate, never dropped

SECOND PREDICTION, REGISTERED AFTER A 4-ROW SMOKE TEST AND BEFORE THE FULL RUN
------------------------------------------------------------------------------
The smoke test (4 rows, sigma=0.25) returned saddle in 4/4 and boundary in 4/4, with
regret roughly tripled. Proposed mechanism: **local signal-to-noise**. Over a small
neighbourhood the latent surface varies little, so at sigma=0.25 the fitted curvature is
dominated by noise, the Hessian is effectively random, and a random symmetric matrix in
4-D is a saddle with high probability. The classical arm escapes this because its CCD
spans the WHOLE factor box, where signal variation is large relative to noise -- the same
spread that makes it readable under a single noisy reading.

This is discriminating, so both noise levels are run:
  * If the cause is local SNR, the saddle rate should fall MATERIALLY at sigma=0.10 and
    the rule should improve relative to measured-value argmax.
  * If the saddle rate stays near 100% at sigma=0.10, the cause is design geometry --
    adaptively clustered points cannot support a second-order fit at any noise level --
    and the rule is dead rather than noise-limited.

Either way this is reported. The sigma=0.10 cell is here to test a stated mechanism, not
to look for a cell where the rule wins.

COMPARATORS, ALL ZERO EXTRA WELLS, ALL ON THE SAME CAMPAIGNS
------------------------------------------------------------
    measured_argmax   the losing baseline, 0.1552 in Q65
    posterior_mean    the existing pooled rule (Q58: -0.0227, not declared)
    local_quadratic   this rule
    doe_measured      the classical arm, 0.0958, gated BIT-EXACT against Q57

The DoE arm is gated at delta 0.0; BO is not gated and cannot be. Stored BO results are
not reproducible from code and seed -- BoTorch's acquisition retry depended on per-process
warning state. Replaying Q57 at its own commit in a byte-identical environment gave some
rows bit-exact and others off by 1.2e-01. The in-run baseline is the BO reference here.

STATUS: EXPLORATORY. n=25 gives MDE ~0.027 > SESOI 0.02. This sizes an effect and cannot
declare equivalence. Gap G2 (n=100) must land before any confirmatory claim.
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
from boec.metrics import constrained_argmax                           # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.rsm import classify_stationary_point, fit_second_order      # noqa: E402
from boec.selection import posterior_mean_at_visited                  # noqa: E402
from boec.surrogate import lengthscales                               # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402

BUDGET = 48
Q = 4
ACQ = "qlognei"
N_INSTANCES = 25
N_SEEDS = 2
M_ACTIVE = 4          # matches the classical arm's 6->4 screen
K_LOCAL = 24          # 15 quadratic terms at m=4, so 9 residual df
DOE_GATE_TOL = 0.0
Q57 = ROOT / "results" / "q57-search-vs-id.json"
OUT = ROOT / "results" / "q66-local-quadratic.json"


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def local_quadratic_pick(model, X: torch.Tensor, Y: torch.Tensor,
                         seed: int) -> tuple[torch.Tensor | None, dict]:
    """Nominate a point from a quadratic fitted to the incumbent's neighbourhood.

    Returns ``(x_nominated or None, diagnostics)``. ``None`` means the local fit was
    rank-deficient; the caller records that as a rate rather than dropping the row.
    """
    d = X.shape[1]
    Xd = X.double()

    def mean_fn(Z):
        with torch.no_grad():
            return model.posterior(Z).mean

    inc = posterior_mean_at_visited(mean_fn, Xd)
    x_inc = Xd[inc]

    ls = lengthscales(model).detach().double().reshape(-1)
    active = torch.argsort(ls)[:M_ACTIVE]                # shortest lengthscale = most active

    # Neighbourhood measured in the active subspace only: distance along a dimension the
    # model considers inert should not decide who is a neighbour.
    dist = torch.cdist(Xd[:, active], x_inc[active].reshape(1, -1)).reshape(-1)
    near = torch.argsort(dist)[:K_LOCAL]

    Xl, Yl = Xd[near][:, active], Y.double()[near]
    diag = dict(incumbent_index=int(inc), active_dims=[int(i) for i in active],
                n_local=int(len(near)))
    try:
        fit = fit_second_order(Xl, Yl)
    except Exception as exc:                             # noqa: BLE001 - recorded as a rate
        return None, dict(diag, fit_failed=f"{type(exc).__name__}: {exc}")

    lo = Xl.amin(dim=0)
    hi = Xl.amax(dim=0)
    hi = torch.where(hi - lo < 1e-9, lo + 1e-6, hi)
    local_box = torch.stack([lo, hi])

    sp = classify_stationary_point(fit.beta, M_ACTIVE, bounds=local_box)
    x_sub, _, _ = constrained_argmax(fit.predict, local_box, seed=seed)

    edge = float(torch.min(torch.minimum(x_sub - lo, hi - x_sub)))
    span = float(torch.min(hi - lo))
    x_full = x_inc.clone()
    x_full[active] = x_sub.double().reshape(-1)
    return x_full.reshape(1, -1), dict(
        diag, fit_failed=None, stationary_kind=str(getattr(sp, "kind", sp)),
        saddle=str(getattr(sp, "kind", sp)) == "saddle",
        on_boundary=bool(edge <= 1e-6 * max(span, 1e-12)))


def one(job: tuple[int, float, int, int]) -> list[dict]:
    dim, sigma, idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=dim)[idx]
    opt = float(inst.optimum_value)

    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    camp = Campaign(o, _bounds(dim),
                    CampaignConfig(d=dim, budget=BUDGET, q=Q, seed=seed,
                                   acq=AcqConfig(kind=ACQ))).run()
    X, Y = camp.train_X, camp.train_Y
    truth = o.truth(X)
    t = truth.double().reshape(-1)
    search = opt - float(t.max())
    base = dict(dim=dim, sigma=sigma, instance=inst.instance_id, instance_index=idx,
                seed=seed, search=search, secs=round(time.time() - t0, 1))

    rows = [dict(base, rule="measured_argmax",
                 regret=opt - float(reported_best_curve(truth, Y)[-1]))]

    model = camp.fit()

    def mean_fn(Z):
        with torch.no_grad():
            return model.posterior(Z).mean

    i_pm = posterior_mean_at_visited(mean_fn, X.double())
    rows.append(dict(base, rule="posterior_mean", regret=opt - float(t[i_pm])))

    x_lq, diag = local_quadratic_pick(model, X, Y, seed)
    rows.append(dict(base, rule="local_quadratic",
                     regret=None if x_lq is None else opt - float(o.truth(x_lq)),
                     **diag))
    for r in rows:
        r["id_gap"] = None if r["regret"] is None else r["regret"] - search
    return rows


def doe_one(job: tuple[int, float, int, int]) -> dict:
    dim, sigma, idx, seed = job
    inst = load_ensemble(dim=dim)[idx]
    opt = float(inst.optimum_value)
    od = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    r = run_doe_arm(od, _bounds(dim), truth=od.truth, budget=BUDGET, seed=seed)
    truth = od.truth(r.X_visited)
    measured = opt - float(reported_best_curve(truth, r.Y_visited)[-1])
    search = opt - float(truth.double().reshape(-1).max())
    return dict(dim=dim, sigma=sigma, instance=inst.instance_id, instance_index=idx,
                seed=seed, rule="doe_measured", regret=measured, search=search,
                id_gap=measured - search, secs=0.0)


def _gate(rows: list[dict]) -> dict:
    stored = {(r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4)): r
              for r in json.loads(Q57.read_text())["rows"]}
    worst, checked = 0.0, 0
    for r in rows:
        if r["rule"] != "doe_measured":
            continue
        k = (r["instance"], r["seed"], r["dim"], round(float(r["sigma"]), 4))
        if k in stored:
            worst = max(worst, abs(r["regret"] - stored[k]["doe_rule_a"]))
            checked += 1
    if checked < 4:
        raise SystemExit(f"DoE gate checked only {checked} rows; not coverage")
    if worst > DOE_GATE_TOL:
        raise SystemExit(f"DoE arm does not reproduce Q57: worst {worst:.3e}; stop.")
    return dict(doe_rows_checked=checked, doe_worst_abs_delta=worst,
                bo_note="BO not gated: stored BO is not reproducible from code+seed.")


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for dim, sigma in sorted({(r["dim"], r["sigma"]) for r in rows}):
        for rule in ("doe_measured", "measured_argmax", "posterior_mean", "local_quadratic"):
            sel = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma
                   and r["rule"] == rule]
            if not sel:
                continue
            ok = [r for r in sel if r["regret"] is not None]
            by: dict[str, list[dict]] = {}
            for r in ok:
                by.setdefault(r["instance"], []).append(r)
            reg = np.array([np.mean([x["regret"] for x in v]) for v in by.values()])
            srch = np.array([np.mean([x["search"] for x in v]) for v in by.values()])
            m, lo, hi = instance_bootstrap(reg)
            rec = dict(dim=dim, sigma=sigma, rule=rule, n=len(by),
                       n_dropped=len(sel) - len(ok),
                       mean_regret=float(m), lo=float(lo), hi=float(hi),
                       mean_search=float(srch.mean()),
                       mean_id_gap=float((reg - srch).mean()))
            if rule == "local_quadratic":
                rec |= dict(
                    fit_failed_rate=float(np.mean([r.get("fit_failed") is not None
                                                   for r in sel])),
                    saddle_rate=float(np.mean([bool(r.get("saddle")) for r in ok])),
                    on_boundary_rate=float(np.mean([bool(r.get("on_boundary"))
                                                    for r in ok])))
            out.append(rec)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--cells", default="6:0.25")
    a = p.parse_args()
    cells = [(int(c.split(":")[0]), float(c.split(":")[1])) for c in a.cells.split(",")]
    jobs = [(d, s, i, sd) for d, s in cells
            for i in range(N_INSTANCES) for sd in range(N_SEEDS)]
    print(f"Q66 PILOT (exploratory) — {len(jobs)} campaigns x 2 arms, {a.workers} workers")
    print(f"  M_ACTIVE={M_ACTIVE}  K_LOCAL={K_LOCAL}  acq={ACQ}\n")

    rows: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        futs |= {ex.submit(doe_one, j): j for j in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            rows.extend(r if isinstance(r, list) else [r])
            if n % 20 == 0 or n == len(futs):
                print(f"  {n}/{len(futs)}  {time.time()-t0:.0f}s", flush=True)

    gate = _gate(rows)
    print(f"\nDoE gate OK: {gate['doe_rows_checked']} rows bit-exact "
          f"(worst {gate['doe_worst_abs_delta']:.3e})\n")
    summary = summarize(rows)
    OUT.write_text(json.dumps(dict(
        ticket="Q66", status="EXPLORATORY PILOT — not a registered result",
        note=("Local quadratic readout on BO's own wells. Zero extra wells. "
              "Q65 showed well-costing interventions are cancelled by lost search."),
        config=dict(budget=BUDGET, q=Q, acq=ACQ, m_active=M_ACTIVE, k_local=K_LOCAL),
        provenance=dict(
            git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
            argv=sys.argv, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        gate=gate, summary=summary, rows=rows), indent=1) + "\n")
    print(f"wrote {OUT}\n")
    for s in summary:
        extra = ""
        if s["rule"] == "local_quadratic":
            extra = (f"  [fit_fail {s['fit_failed_rate']:.0%} "
                     f"saddle {s['saddle_rate']:.0%} edge {s['on_boundary_rate']:.0%}]")
        print(f"  {s['rule']:<17} regret {s['mean_regret']:.4f} "
              f"[{s['lo']:.4f},{s['hi']:.4f}]  search {s['mean_search']:.4f}  "
              f"id_gap {s['mean_id_gap']:.4f}{extra}")


if __name__ == "__main__":
    main()
