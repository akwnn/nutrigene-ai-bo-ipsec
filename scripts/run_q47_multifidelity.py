"""Q47 — where a cheap second readout stops paying. A threshold surface, not a method.

    python scripts/run_q47_multifidelity.py --shard 6-0.25-10   # one (d, sigma, cost)
    python scripts/run_q47_multifidelity.py --merge             # reassemble + report

Registered in `docs/OPEN-QUESTIONS.md` Q47 **before this file existed**, together with a
prediction computed by `scripts/q47_predict_threshold.py`. Read the registration first;
it records three corrections to the brief and one measurement that reframes the sweep.

WHAT IS BEING ASKED
-------------------
Not "does multi-fidelity help" — that answer is whatever correlation you assume, and no
correlation is published for endothelial differentiation. Instead: **sweep the
correlation and the cost ratio and report where the two-tier design stops winning.** A
lab can measure its own correlation in a morning and read off which side of the line it
is on.

THE LINE THAT MATTERS MOST IS NOT THE THRESHOLD
-----------------------------------------------
The expensive readout is not a gold standard. Under this project's own observation model
its correlation with the truth is **0.583 at sigma_rel=0.25** and **0.872 at 0.10**.
Above that, a "cheap" readout is simply *more accurate and also cheaper*, and the
recommendation is to stop running the expensive one. That line is reported on every
surface, and a two-tier arm LOSING above it is a harness bug rather than a finding.

EQUAL TOTAL COST, NEVER EQUAL EVALUATION COUNT
-----------------------------------------------
Asserted per arm per run by `multifidelity.Allocation`, not assumed. The one arm that
deliberately spends less is `budget_only`, which is the control for "what does simply
cutting the expensive budget cost, before any cheap tier enters".

COMMON RANDOM NUMBERS
---------------------
The calibration `(a, b)`, every design, and the cheap readout's noise draw `z` depend
only on `(instance, seed)` — never on rho. So a contrast between two rho levels is a
pure rho effect with the design and the noise held identical, and the pairing survives
into the instance-level bootstrap.
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

from scipy.stats import wilcoxon                                   # noqa: E402
from torch.quasirandom import SobolEngine                          # noqa: E402

from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.metrics import constrained_argmax                        # noqa: E402
from boec.multifidelity import (                                   # noqa: E402
    CheapTier,
    allocate,
    cheap_sigma,
    draw_cheap,
    recalibrate,
    signal_sd,
    split_confirm,
    top_k,
)
from boec.optimizers import lhs_design                             # noqa: E402
from boec.oracles import load_ensemble                             # noqa: E402
from boec.surrogate import build_gp                                # noqa: E402
from boec.torch_oracle import BiphasicOracle                       # noqa: E402

BUDGET = 48
PHI = 1.0 / 3.0                       # cheap tier's share of the budget
N_INSTANCES, N_SEEDS = 25, 2
RHOS = (0.30, 0.45, 0.55, 0.65, 0.80, 0.95)
COST_RATIOS = (3, 5, 10, 20)
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
N_RESTARTS, RAW_SAMPLES = 20, 4096
N_CHECK = 4096                        # Sobol sample for sigma_f and the achieved rho
RHO_TOL = 0.02
A_RANGE, B_RANGE = (0.5, 2.0), (-0.5, 0.5)
RULE = "=" * 104

# measured; see the Q47 registration and results/q47-prediction.log
RHO_EXPENSIVE = {(6, 0.25): 0.583, (6, 0.10): 0.872,
                 (8, 0.25): 0.557, (8, 0.10): 0.863}


def _seed_of(instance_id: str, seed: int, salt: int) -> int:
    return (int(instance_id[:8], 16) * 1000 + seed * 7 + salt) % (2**31 - 1)


def _rule_a(truth: torch.Tensor, obs: torch.Tensor, opt: float) -> float:
    """Regret of the point the method would hand you: chosen by observation."""
    return opt - float(reported_best_curve(truth, obs)[-1])


def _rule_c(X: torch.Tensor, Y: torch.Tensor, Yvar: torch.Tensor,
            bounds: torch.Tensor, oracle, opt: float, seed: int) -> tuple[float, str]:
    """Regret at the fitted surface's own argmax. Failures are recorded, never dropped."""
    try:
        model = build_gp(X, Y, Yvar, bounds)

        def mean(Z: torch.Tensor) -> torch.Tensor:
            with torch.no_grad():
                return model.posterior(Z).mean

        x, _, _ = constrained_argmax(mean, bounds, n_restarts=N_RESTARTS,
                                     raw_samples=RAW_SAMPLES, seed=seed)
        return opt - float(oracle.truth(x.reshape(1, -1))), ""
    except Exception as exc:                            # noqa: BLE001 - recorded
        return float("nan"), f"{type(exc).__name__}: {exc}"


def _expensive(oracle, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor,
                                                 torch.Tensor]:
    Y, Yvar = oracle.evaluate(X)
    return Y, Yvar, oracle.truth(X)


def run_shard(dim: int, sigma: float, cost_ratio: int, *, phi: float = PHI,
              fixed_calibration: bool = False) -> list[dict]:
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    alloc = allocate(budget=BUDGET, cost_ratio=cost_ratio, phi=phi)
    assert alloc.spent == BUDGET, f"two-tier arms spend {alloc.spent}, not {BUDGET}"
    k, n_cheap = alloc.n_expensive, alloc.n_cheap
    check_X = SobolEngine(dimension=dim, scramble=True, seed=0).draw(N_CHECK).double()
    rows: list[dict] = []

    for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
        opt = float(inst.optimum_value)
        diag = BiphasicOracle(inst, sigma_rel=sigma, seed=999)
        f_check = diag.truth(check_X).numpy().ravel()
        y_check, _ = diag.evaluate(check_X)
        y_check = y_check.numpy().ravel()
        sf = signal_sd(f_check)

        for seed in range(N_SEEDS):
            rng = np.random.default_rng(_seed_of(inst.instance_id, seed, 1))
            a = 1.0 if fixed_calibration else float(rng.uniform(*A_RANGE))
            b = 0.0 if fixed_calibration else float(rng.uniform(*B_RANGE))
            z_check = rng.standard_normal(N_CHECK)
            z_cheap = rng.standard_normal(n_cheap)
            d_seed = _seed_of(inst.instance_id, seed, 2)

            base = dict(instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                        cost_ratio=cost_ratio, n_cheap=n_cheap, k=k, phi=phi,
                        a=a, b=b, sigma_f=sf,
                        fixed_calibration=bool(fixed_calibration))

            # ---- single tier: the full expensive budget on a space-filling design ----
            X1 = lhs_design(bounds, BUDGET, seed=d_seed)
            o1 = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            Y1, V1, T1 = _expensive(o1, X1)
            single_a = _rule_a(T1, Y1, opt)
            single_c, single_f = _rule_c(X1, Y1, V1, bounds, o1, opt, d_seed)

            # ---- the under-budget control: 32 expensive points and nothing bought ----
            Xb = lhs_design(bounds, k, seed=d_seed)
            ob = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            Yb, Vb, Tb = _expensive(ob, Xb)
            budget_a = _rule_a(Tb, Yb, opt)
            budget_c, budget_f = _rule_c(Xb, Yb, Vb, bounds, ob, opt, d_seed)

            # ---- the cheap tier ----
            Xc = lhs_design(bounds, n_cheap, seed=d_seed)
            oc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            f_cheap = oc.truth(Xc).numpy().ravel()

            for rho in RHOS:
                tier = CheapTier(a=a, b=b, sigma_cheap=cheap_sigma(a, sf, rho),
                                 rho_target=rho)
                # achieved correlation, on the large fixed sample so it is precise
                yc_check = draw_cheap(f_check, tier, z=z_check)
                rho_true = float(np.corrcoef(yc_check, f_check)[0, 1])
                rho_obs = float(np.corrcoef(yc_check, y_check)[0, 1])
                if abs(rho_true - rho) > RHO_TOL:
                    raise AssertionError(
                        f"achieved rho {rho_true:.4f} != target {rho} on "
                        f"{inst.instance_id} (d={dim} sigma={sigma})")

                y_cheap = draw_cheap(f_cheap, tier, z=z_cheap)
                row = dict(base, rho=rho, rho_true=rho_true, rho_obs=rho_obs,
                           single_a=single_a, single_c=single_c,
                           single_c_failure=single_f,
                           budget_only_a=budget_a, budget_only_c=budget_c,
                           budget_only_c_failure=budget_f)

                # ---- screen then confirm: top k by cheap value, GP on expensive only --
                sel = top_k(y_cheap, k)
                Xs = Xc[sel]
                os_ = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                Ys, Vs, Ts = _expensive(os_, Xs)
                row["screen_a"] = _rule_a(Ts, Ys, opt)
                row["screen_c"], row["screen_c_failure"] = _rule_c(
                    Xs, Ys, Vs, bounds, os_, opt, d_seed)

                # ---- joint: split confirmations, cheap tier recalibrated and pooled ---
                jrng = np.random.default_rng(_seed_of(inst.instance_id, seed, 3))
                jsel = split_confirm(y_cheap, k, jrng)
                Xj = Xc[jsel]
                oj = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                Yj, Vj, Tj = _expensive(oj, Xj)
                row["joint_a"] = _rule_a(Tj, Yj, opt)
                rest = np.setdiff1d(np.arange(n_cheap), jsel, assume_unique=False)
                rc = recalibrate(
                    cheap_paired=y_cheap[jsel], exp_paired=Yj.numpy().ravel(),
                    cheap_all=y_cheap[rest], yvar_exp=Vj.numpy().ravel(),
                    sigma_add=oj.sigma_add)
                Xp = torch.cat([Xj, Xc[rest]])
                Yp = torch.cat([Yj, torch.from_numpy(rc.pseudo.reshape(-1, 1))])
                Vp = torch.cat([Vj, torch.full((rest.size, 1), rc.variance,
                                               dtype=torch.double)])
                row["joint_pseudo_var"] = rc.variance
                row["joint_resid_var"] = rc.resid_var
                row["joint_mean_yvar"] = rc.mean_yvar
                row["joint_slope"] = rc.slope
                # oracle-truth pseudo-error variance, sf^2 (1 - rho^2). DIAGNOSTIC ONLY:
                # never seen by any arm. It exists to measure how conservative the
                # estimator above is, rather than leaving that asserted.
                row["joint_pseudo_var_oracle"] = float(sf**2 * (1.0 - rho_true**2))
                row["joint_n_train"] = int(Xp.shape[0])
                row["joint_c"], row["joint_c_failure"] = _rule_c(
                    Xp, Yp, Vp, bounds, oj, opt, d_seed)
                rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

ARMS = ("single", "budget_only", "screen", "joint")


def _paired(rows: list[dict], a: str, b: str) -> dict | None:
    """Instance-level paired contrast: b - a, so positive means `a` has less regret."""
    insts = sorted({r["instance"] for r in rows})
    va, vb = [], []
    for i in insts:
        g = [r for r in rows if r["instance"] == i]
        xa = [r[a] for r in g if r[a] is not None and np.isfinite(r[a])]
        xb = [r[b] for r in g if r[b] is not None and np.isfinite(r[b])]
        if len(xa) != len(g) or len(xb) != len(g):
            continue
        va.append(np.mean(xa))
        vb.append(np.mean(xb))
    if len(va) < 3:
        return None
    diff = np.array(vb) - np.array(va)
    m, lo, hi = instance_bootstrap(diff, n_boot=2000)
    try:
        p = float(wilcoxon(diff).pvalue)
    except ValueError:
        p = float("nan")
    return dict(diff=float(m), lo=float(lo), hi=float(hi), p=p, n=int(len(diff)),
                verdict="better" if lo > 0 else ("worse" if hi < 0 else "null"))


def _crossing(effects: list[tuple[float, dict | None]]) -> str:
    """Lowest rho at which the arm's advantage is significant, bracketed by grid points."""
    prev = None
    for rho, e in effects:
        if e is None:
            continue
        if e["verdict"] == "better":
            return f"<= {rho:.2f}" if prev is None else f"{prev:.2f} - {rho:.2f}"
        prev = rho
    return "never in range"


def report(rows: list[dict]) -> list[dict]:
    out = []
    for dim, sigma in CELLS:
        cell = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12]
        if not cell:
            continue
        rho_e = RHO_EXPENSIVE[(dim, sigma)]
        print(f"\n{RULE}\nQ47 · d={dim} · sigma_rel={sigma} · budget {BUDGET} "
              f"expensive-equivalents · phi={PHI:.3f}\n{RULE}")
        print(f"  corr(expensive observation, truth) = {rho_e:.3f}  <-- ABOVE THIS THE "
              f"CHEAP READOUT IS THE BETTER ASSAY")
        m = [(r["rho"], r["rho_obs"]) for r in cell]
        print("  rho to truth -> rho a lab can actually measure (vs the expensive "
              "readout):")
        print("     " + "   ".join(
            f"{t:.2f}->{np.mean([o for tt, o in m if tt == t]):.2f}" for t in RHOS))

        for rule, tag in (("a", "RULE A  (reported best)"), ("c", "RULE C  (GP argmax)")):
            print(f"\n  {tag}")
            base = np.mean([r[f"single_{rule}"] for r in cell])
            bo = np.mean([r[f"budget_only_{rule}"] for r in cell])
            print(f"    single tier, 48 expensive          regret {base:.4f}"
                  f"        <- the thing to beat")
            print(f"    32 expensive only, nothing bought  regret {bo:.4f}"
                  f"        <- under-budget control (32/48)")
            for c in COST_RATIOS:
                sub_c = [r for r in cell if r["cost_ratio"] == c]
                if not sub_c:
                    continue
                n_cheap = sub_c[0]["n_cheap"]
                print(f"\n    cost ratio {c:>2}x   ({n_cheap} cheap + "
                      f"{sub_c[0]['k']} expensive = {BUDGET} expensive-equivalents)")
                eff = {"screen": [], "joint": []}
                for rho in RHOS:
                    sub = [r for r in sub_c if abs(r["rho"] - rho) < 1e-12]
                    if not sub:
                        continue
                    flag = "  *" if rho > rho_e else ""
                    parts = []
                    for arm in ("screen", "joint"):
                        e = _paired(sub, f"{arm}_{rule}", f"single_{rule}")
                        eff[arm].append((rho, e))
                        parts.append(
                            f"{arm} {np.mean([r[f'{arm}_{rule}'] for r in sub]):.4f} "
                            f"({e['diff']:+.4f} [{e['lo']:+.4f},{e['hi']:+.4f}] "
                            f"{e['verdict']})" if e else f"{arm} n/a")
                    print(f"      rho={rho:.2f}{flag:<4} " + "   ".join(parts))
                for arm in ("screen", "joint"):
                    print(f"        -> {arm} beats single tier from rho "
                          f"{_crossing(eff[arm])}")
                out.append(dict(dim=dim, sigma=sigma, cost_ratio=c, rule=rule,
                                rho_expensive=rho_e,
                                crossing={a: _crossing(eff[a]) for a in eff}))
        fails = sum(1 for r in cell for a in ARMS if r.get(f"{a}_c_failure"))
        print(f"\n  rule-C fit failures in this cell: {fails} of {len(cell) * 4}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", help="d-sigma-cost, e.g. 6-0.25-10")
    ap.add_argument("--phi", type=float, default=PHI,
                    help="cheap tier's share of the budget; 1/3 is the registered primary")
    ap.add_argument("--fixed-calibration", action="store_true",
                    help="a=1, b=0 instead of sampled -- the sensitivity arm")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    outdir = ROOT / "results"

    if args.merge:
        rows, missing = [], []
        for dim, sigma in CELLS:
            for c in COST_RATIOS:
                p = outdir / f"q47-mf-{dim}-{sigma}-{c}.json"
                if p.exists():
                    rows.extend(json.loads(p.read_text()))
                else:
                    missing.append(p.name)
        if missing:
            print(f"  MISSING {len(missing)} shards: {', '.join(missing)}")
        summary = report(rows)
        (outdir / "q47-multifidelity.json").write_text(
            json.dumps(dict(rows=rows, summary=summary, missing=missing), indent=1))
        print(f"\n  {len(rows)} rows -> results/q47-multifidelity.json")
        return

    dim, sigma, cost = args.shard.split("-")
    t0 = time.time()
    rows = run_shard(int(dim), float(sigma), int(cost), phi=args.phi,
                     fixed_calibration=args.fixed_calibration)
    tag = ""
    if abs(args.phi - PHI) > 1e-9:
        tag += f"-phi{args.phi:.2f}"
    if args.fixed_calibration:
        tag += "-fixedcal"
    out = outdir / f"q47-mf-{dim}-{sigma}-{cost}{tag}.json"
    out.write_text(json.dumps(rows, indent=1))
    print(f"  shard {args.shard}{tag}: {len(rows)} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
