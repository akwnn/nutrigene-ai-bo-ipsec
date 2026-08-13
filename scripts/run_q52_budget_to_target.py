"""Q52 §2 — budget-to-target curves. BO against the classical pipeline.

    python scripts/run_q52_budget_to_target.py [n_instances]

Design registered in `docs/OPEN-QUESTIONS.md` (df11ad6, amended d86e2c2) BEFORE this
file produced a number. Four arms, cap 200, d=6, sigma_rel in {0.10, 0.25}, n=25.

WHY THE ONE-SHOT ARMS ARE RE-DRAWN AT EACH CHECKPOINT
------------------------------------------------------
A one-shot space-filling design has no regret *curve*: the first n points of a
200-point Latin hypercube are not a Latin hypercube on n points, and scoring them as
one would report a stratification the lab never had. The faithful question for a
one-shot arm is "if you committed to n measurements up front, what would you get", so a
fresh design of size n is drawn at each checkpoint. The adaptive arm IS prefixed,
because a campaign genuinely passes through its own n=24 state on the way to 200.

`optimizers.lhs_design` / `random_design` are called directly rather than
`runner.static_design`, which refuses any budget below the d=6 opening of 14 and would
make checkpoints 8 and 12 unreachable for a one-shot arm. Caught by the smoke test.

DESIGNS ARE DRAWN PER INSTANCE — A DELIBERATE DEVIATION FROM E2
----------------------------------------------------------------
Q48 established that E2 scored all 25 instances of a cell on the IDENTICAL points, and
that `lhs` sat at the 0th percentile of 60 draws there. Repeating that would make every
one-shot arrival a property of two draws. The design seed is a function of the instance
id, so these intervals are between-design rather than within-design.

PROVENANCE IS STAMPED, WHICH NO OTHER RESULTS FILE IN THIS REPO DOES
---------------------------------------------------------------------
All 64 committed JSON artifacts record no git SHA, no timestamp, no config and no
library versions. This one does.
"""

from __future__ import annotations

import json
import math
import os
import platform
import subprocess
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

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target  # noqa: E402
from boec.campaign import Campaign, CampaignConfig                # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe_repeat import PIPELINE_BUDGET, run_doe_repeat       # noqa: E402
from boec.metrics import constrained_argmax                       # noqa: E402
from boec.optimizers import lhs_design, random_design             # noqa: E402
from boec.oracles import load_ensemble                            # noqa: E402
from boec.surrogate import build_gp                               # noqa: E402
from boec.torch_oracle import BiphasicOracle                      # noqa: E402

DIM = 6
SIGMAS = (0.25, 0.10)
N_INSTANCES = 25
CAP = 200
CHECKPOINTS = (8, 12, 16, 20, 24, 32, 48, 64, 100, 150, 200)
#: Registered split. The full cross product is computed; these are the headline sets.
TARGETS_RULE_C = (0.30, 0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05)
TARGETS_RULE_A = (0.03, 0.02, 0.01)
ALL_TARGETS = tuple(sorted(set(TARGETS_RULE_C) | set(TARGETS_RULE_A), reverse=True))
ARMS = ("qlogei", "doe", "random", "spread_gp")
N_RESTARTS, RAW_SAMPLES = 20, 4096
WORKERS = 4
N_BOOT = 4000
CENSOR_LIMIT = 0.50   # above this, report the rate and no point estimate
RULE = "=" * 100
OUT = ROOT / "results" / "q52-budget-to-target.json"
E2_GRID = ROOT / "results" / "e2-grid.json"


def _seed_of(instance_id: str, salt: int) -> int:
    return (int(instance_id[:8], 16) * 1000 + salt) % (2**31 - 1)


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(DIM, dtype=torch.double),
                        torch.ones(DIM, dtype=torch.double)])


def rounds_for(arm: str, n: int) -> int:
    """Sequential plate cycles to spend ``n`` evaluations. Q38: a lab pays in rounds."""
    if arm == "doe":
        return 3 * (n // PIPELINE_BUDGET)          # screen, response-surface, confirm
    if arm == "qlogei":
        n_init = 2 * DIM + 2                        # 14 at d=6
        return 1 if n <= n_init else 1 + math.ceil((n - n_init) / 4)
    return 1                                        # one-shot designs


def _provenance() -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return dict(
        git_sha=_git("rev-parse", "HEAD"),
        git_dirty=bool(_git("status", "--porcelain")),
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        argv=sys.argv, python=platform.python_version(),
        torch=torch.__version__, botorch=botorch.__version__,
        gpytorch=gpytorch.__version__, numpy=np.__version__, scipy=scipy.__version__,
        config=dict(dim=DIM, sigmas=list(SIGMAS), n_instances=N_INSTANCES, cap=CAP,
                    checkpoints=list(CHECKPOINTS), arms=list(ARMS),
                    targets_rule_c=list(TARGETS_RULE_C),
                    targets_rule_a=list(TARGETS_RULE_A),
                    censor_limit=CENSOR_LIMIT, n_boot=N_BOOT),
    )


def _gp_recommendation(X, Y, V, bounds, orac, opt, seed) -> float:
    model = build_gp(X, Y, V, bounds)

    def mean(Z, _m=model):
        with torch.no_grad():
            return _m.posterior(Z).mean

    x, _, _ = constrained_argmax(mean, bounds, n_restarts=N_RESTARTS,
                                 raw_samples=RAW_SAMPLES, seed=seed)
    return opt - float(orac.truth(x.reshape(1, -1)))


def fidelity_gate(n_check: int = 5) -> dict:
    """Reproduce E2's stored qLogEI rows before any new number is trusted (Q50)."""
    rows = json.loads(E2_GRID.read_text())
    want = {(r["instance"], r["seed"]): r["regret"] for r in rows
            if r["arm"] == "qlogei" and r["dim"] == DIM and r["sigma"] == 0.25}
    bounds = _bounds()
    deltas = []
    for inst in load_ensemble(dim=DIM)[:n_check]:
        for seed in (0, 1):
            key = (inst.instance_id, seed)
            if key not in want:
                continue
            o = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
            c = Campaign(o, bounds, CampaignConfig(d=DIM, budget=48, q=4, seed=seed))
            c.run()
            got = float(inst.optimum_value) - float(
                reported_best_curve(o.truth(c.train_X), c.train_Y)[-1])
            deltas.append(abs(got - want[key]))
    return dict(n=len(deltas), max_abs_delta=max(deltas) if deltas else None)


def one(job: tuple[int, float]) -> dict:
    """One instance x one noise level: four arms, every checkpoint, both rules."""
    instance_index, sigma = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM)[instance_index]
    opt = float(inst.optimum_value)
    bounds = _bounds()
    base = _seed_of(inst.instance_id, 0) % 10_000
    arms: dict[str, dict] = {}

    # --- qlogei: one capped campaign, prefixed ---------------------------------
    orac = BiphasicOracle(inst, sigma_rel=sigma, seed=base)
    camp = Campaign(orac, bounds, CampaignConfig(d=DIM, budget=CAP, q=4, seed=base))
    camp.run()
    X, Y, V = camp.train_X, camp.train_Y, camp.train_Yvar
    if int(X.shape[0]) != CAP:
        raise RuntimeError(f"campaign returned {int(X.shape[0])}, expected {CAP}")
    curve = reported_best_curve(orac.truth(X), Y)
    ra, rc = {}, {}
    for n in CHECKPOINTS:
        ra[n] = opt - float(curve[n - 1])
        rc[n] = _gp_recommendation(X[:n], Y[:n], V[:n], bounds, orac, opt,
                                   _seed_of(inst.instance_id, n))
    arms["qlogei"] = dict(rule_a=ra, rule_c=rc)

    # --- doe: repeat the pipeline, keep the best -------------------------------
    orac_d = BiphasicOracle(inst, sigma_rel=sigma, seed=base)
    dr = run_doe_repeat(
        orac_d, bounds, truth=orac_d.truth, optimum_value=opt, cap=CAP, seed=base,
        seeds=tuple(_seed_of(inst.instance_id, 7000 + i)
                    for i in range(CAP // PIPELINE_BUDGET)))
    arms["doe"] = dict(rule_a=dr.rule_a, rule_c=dr.rule_c_unconstrained,
                       rule_c_constrained=dr.rule_c_constrained,
                       n_pipelines=dr.n_pipelines,
                       evaluations_spent=dr.evaluations_spent)

    # --- random and spread+GP: a fresh design of size n at each checkpoint ------
    for arm, maker in (("random", random_design), ("spread_gp", lhs_design)):
        a_curve, c_curve = {}, {}
        for n in CHECKPOINTS:
            o = BiphasicOracle(inst, sigma_rel=sigma, seed=base)
            s = _seed_of(inst.instance_id, n)
            Xs = maker(bounds, n, seed=s)
            Ys, Vs = o.evaluate(Xs)
            a_curve[n] = opt - float(reported_best_curve(o.truth(Xs), Ys)[-1])
            if arm == "spread_gp":
                c_curve[n] = _gp_recommendation(Xs, Ys, Vs, bounds, o, opt, s)
        arms[arm] = dict(rule_a=a_curve) | ({"rule_c": c_curve} if c_curve else {})

    secs = round(time.time() - t0, 1)
    print(f"    inst {instance_index:>2} s={sigma:<5} {secs:>6.0f}s  "
          f"qlogei A {ra[24]:.4f}->{ra[200]:.4f}  C {rc[24]:.4f}->{rc[200]:.4f}  "
          f"doe A@192 {dr.rule_a[192]:.4f}", flush=True)
    return dict(instance_index=instance_index, instance_id=inst.instance_id,
                sigma=sigma, seed=base, secs=secs, arms=arms)


def _arrivals(rows, arm, rule, target):
    out = []
    for r in rows:
        c = r["arms"].get(arm, {}).get(rule)
        if c is not None:
            out.append(first_budget_to_target(c, target=target, cap=CAP))
    return out


def _cell(arrivals, arm):
    """(display, median_or_None, censored_fraction). Registered censoring rules."""
    if not arrivals:
        return "—", None, 1.0
    got = [a for a in arrivals if a is not ARRIVAL_CENSORED]
    frac = 1.0 - len(got) / len(arrivals)
    if frac > CENSOR_LIMIT:
        return f"cens {frac:.0%}", None, frac
    med = float(np.median(got))
    rnd = rounds_for(arm, int(med))
    tag = "" if frac == 0 else "*"
    return f"{int(med)}{tag}/{rnd}r", med, frac


def report(rows, sigma) -> None:
    rows = [r for r in rows if r["sigma"] == sigma]
    if not rows:
        return
    print(f"\n{RULE}\n  d={DIM}  sigma_rel={sigma}  n={len(rows)} instances  "
          f"cap={CAP} (registered compute limit)\n{RULE}")
    print("  cells read  evaluations/rounds ; * = some instances censored ; "
          f"cens = >{CENSOR_LIMIT:.0%} censored, no point estimate")

    for rule, headline in (("rule_c", TARGETS_RULE_C), ("rule_a", TARGETS_RULE_A)):
        label = "RULE C — posterior mean" if rule == "rule_c" else "RULE A — best observed"
        print(f"\n  {label}   (headline targets: "
              f"{', '.join(f'{t:g}' for t in headline)})")
        # (label, arm, curve-key). Q41: all three scorings reported in every table.
        cols = [(a, a, rule) for a in ARMS
                if any(rule in r["arms"].get(a, {}) for r in rows)]
        if rule == "rule_c":
            cols.insert(2, ("doe(con)", "doe", "rule_c_constrained"))
        hdr = f"    {'target':>7}"
        for label, _, _ in cols:
            hdr += f"{label:>17}"
        hdr += f"{'savings':>11}{'n_pair':>8}"
        print(hdr)
        for t in ALL_TARGETS:
            mark = "*" if t in headline else " "
            line = f"  {mark} {t:>6.2f}"
            arr = {}
            for label, a, key in cols:
                arr[label] = _arrivals(rows, a, key, t)
                line += f"{_cell(arr[label], a)[0]:>17}"
            bo, doe = arr.get("qlogei", []), arr.get("doe", [])
            pairs = [d / b for b, d in zip(bo, doe)
                     if b is not ARRIVAL_CENSORED and d is not ARRIVAL_CENSORED]
            if pairs and len(pairs) / max(len(bo), 1) >= (1 - CENSOR_LIMIT):
                m, lo, hi = instance_bootstrap(np.array(pairs), n_boot=N_BOOT)
                line += f"{m:>11.2f}{len(pairs):>8}"
            else:
                line += f"{'undef':>11}{len(pairs):>8}"
            print(line)
        print("    savings = DoE evaluations / BO evaluations, paired per instance, "
              "complete cases only.")
        print("    undefined wherever either arm is censored — the cap is never "
              "substituted for an arrival.")


def main() -> None:
    n_inst = int(sys.argv[1]) if len(sys.argv) > 1 else N_INSTANCES
    print(f"{RULE}\nQ52 §2 — budget-to-target. Four arms against the classical "
          f"pipeline.\n{RULE}")
    print(f"  d={DIM}, sigma in {SIGMAS}, {n_inst} instances, cap {CAP}, arms {ARMS}")
    print(f"  checkpoints {CHECKPOINTS}")

    print("\n  FIDELITY GATE — reproducing E2's stored qLogEI rows (Q50's check)")
    gate = fidelity_gate()
    print(f"    {gate['n']} rows re-run at budget 48, max |delta| = "
          f"{gate['max_abs_delta']:.3e}\n")

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["instance_index"], r["sigma"]) for r in done}
    todo = [(i, s) for s in SIGMAS for i in range(n_inst) if (i, s) not in have]
    if have:
        print(f"  resuming — {len(have)} instance-cells already on disk\n")

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for row in pool.map(one, todo):
            done.append(row)
            OUT.write_text(json.dumps(
                dict(provenance=_provenance(), fidelity_gate=gate, rows=done), indent=1))

    for s in SIGMAS:
        report(done, s)
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
