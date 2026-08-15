"""Q54 — Hill `spread_gp` at five design draws. Is the Q52 match one lucky Latin hypercube?

    python scripts/run_q54_hill_spread_gp_draws.py [n_instances]
    python scripts/run_q54_hill_spread_gp_draws.py --gate-only     # draw 0 vs Q52, then stop
    python scripts/run_q54_hill_spread_gp_draws.py --time-one      # one instance-cell, then stop

WHAT THIS CLOSES
----------------
Q52 ran the one-shot arm on the Hill family with **one design draw** and found its
arrival hit-rate matching 10-round qLogEI's. Q53 then ran the same arm on four external
families at **five** draws and found design SDs of 0.029–0.153 — large enough that a
single draw is not quotable, which is why `spread_gp.design_average` returns ``nan``
rather than ``0.0`` for one draw. Those two facts cannot be pooled: the Hill claim rests
on n=1 from a lottery the external families showed to be wide.

`docs/PROMPTS-NEXT.md` Prompt 3 registers the fix and the constraint: re-run Hill at five
draws, same checkpoints, targets and instances as Q52, and **until this exists the paper
may report the current match and must not generalise it.**

THE GATE IS FREE, SO IT IS NOT OPTIONAL
----------------------------------------
Draw 0 uses Q52's own design seed, ``_seed_of(instance_id, n)``, with the oracle pinned at
Q52's ``base``. It must therefore reproduce the committed ``q52-budget-to-target.json``
spread_gp curves **exactly**. That makes Q52's draw one member of this study's five rather
than a separate number that happens to sit nearby, and it gates the whole re-run: if draw 0
does not come back identical, this script is not running Q52's arm and none of draws 1–4
describe it either. Same discipline as `rescore_d20.py`'s untouched-column gate.

WHAT VARIES, AND WHAT DELIBERATELY DOES NOT
---------------------------------------------
Only the **design draw** moves. The oracle's noise seed stays at Q52's ``base`` for every
draw, so this measures the Latin-hypercube lottery (Q48/D16) and not a second, confounded
noise lottery on top of it. qLogEI is **not re-run**: its curves are read from the
committed Q52 rows, on the same instances, so the contrast stays paired.

THE ACTUAL QUESTION IS VERDICT STABILITY
------------------------------------------
A mean and an SD over five draws is the smaller half of the answer. The registered
question is whether the *yes/no* verdict — "the one-shot arm arrives as often as the
adaptive one" — survives redrawing the design. So the per-draw McNemar verdict is
reported for all five draws at every target, and the headline is how many of the five
agree. A match that holds on one draw in five is not a match.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target   # noqa: E402
from boec.diagnostics import reported_best_curve                   # noqa: E402
from boec.metrics import constrained_argmax                        # noqa: E402
from boec.optimizers import lhs_design                             # noqa: E402
from boec.oracles import load_ensemble                             # noqa: E402
from boec.spread_gp import design_average                          # noqa: E402
from boec.surrogate import build_gp                                # noqa: E402
from boec.torch_oracle import BiphasicOracle                       # noqa: E402

# --- everything below is copied from Q52 and must not drift -------------------
DIM = 6
SIGMAS = (0.25, 0.10)
N_INSTANCES = 25
CAP = 200
CHECKPOINTS = (8, 12, 16, 20, 24, 32, 48, 64, 100, 150, 200)
TARGETS_RULE_C = (0.30, 0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05)
TARGETS_RULE_A = (0.03, 0.02, 0.01)
N_RESTARTS, RAW_SAMPLES = 20, 4096
CENSOR_LIMIT = 0.50

#: Q53 used five. Matching it is the point — the two studies are then one design lottery
#: measured on five families, not two studies at different resolutions.
N_DRAWS = 5
#: Draw 0 is Q52's own seed. Later draws are offset by a stride far larger than any
#: checkpoint so that draw d at checkpoint n can never collide with draw 0 at some other
#: checkpoint, which would silently correlate two supposedly independent draws.
DRAW_STRIDE = 100_000
GATE_TOL = 1e-12

OUT = ROOT / "results" / "q54-hill-spread-gp-draws.json"
Q52 = ROOT / "results" / "q52-budget-to-target.json"
RULE = "=" * 100


def _seed_of(instance_id: str, salt: int) -> int:
    """Q52's seed function, verbatim. Any change here breaks the draw-0 gate."""
    return (int(instance_id[:8], 16) * 1000 + salt) % (2**31 - 1)


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(DIM, dtype=torch.double),
                        torch.ones(DIM, dtype=torch.double)])


def rounds_for_spread_gp(_n: int) -> int:
    """One. The whole design is plated at once — that is the arm's entire claim."""
    return 1


def rounds_for_qlogei(n: int) -> int:
    """Q52's `rounds_for`, qLogEI branch, verbatim."""
    n_init = 2 * DIM + 2
    return 1 if n <= n_init else 1 + math.ceil((n - n_init) / 4)


def _provenance(args) -> dict:
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
        config=dict(dim=DIM, sigmas=list(SIGMAS), n_instances=args.n_instances,
                    cap=CAP, checkpoints=list(CHECKPOINTS), n_draws=N_DRAWS,
                    draw_stride=DRAW_STRIDE, gate_tol=GATE_TOL,
                    targets_rule_c=list(TARGETS_RULE_C),
                    targets_rule_a=list(TARGETS_RULE_A),
                    censor_limit=CENSOR_LIMIT,
                    n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES,
                    source=Q52.name),
    )


def _draw_seed(instance_id: str, n: int, draw: int) -> int:
    return _seed_of(instance_id, n + DRAW_STRIDE * draw)


def one_draw(inst, sigma: float, draw: int) -> dict:
    """One instance x one noise level x one design draw: both rules at every checkpoint.

    The body is Q52's ``one()`` spread_gp branch with the design seed carrying a draw
    offset. Nothing else moves.
    """
    opt = float(inst.optimum_value)
    bounds = _bounds()
    base = _seed_of(inst.instance_id, 0) % 10_000

    a_curve, c_curve = {}, {}
    for n in CHECKPOINTS:
        o = BiphasicOracle(inst, sigma_rel=sigma, seed=base)
        s = _draw_seed(inst.instance_id, n, draw)
        Xs = lhs_design(bounds, n, seed=s)
        Ys, Vs = o.evaluate(Xs)
        a_curve[n] = opt - float(reported_best_curve(o.truth(Xs), Ys)[-1])

        model = build_gp(Xs, Ys, Vs, bounds)

        def mean(Z, _m=model):
            with torch.no_grad():
                return _m.posterior(Z).mean

        x, _, _ = constrained_argmax(mean, bounds, n_restarts=N_RESTARTS,
                                     raw_samples=RAW_SAMPLES, seed=s)
        c_curve[n] = opt - float(o.truth(x.reshape(1, -1)))
    return dict(rule_a=a_curve, rule_c=c_curve)


def gate_draw_zero(rows: list[dict], stored: list[dict]) -> dict:
    """Draw 0 must reproduce the committed Q52 spread_gp curves exactly.

    Raises rather than warning. A drifted draw 0 means the arm being measured here is not
    the arm Q52 measured, and then draws 1-4 are five samples from some other lottery.
    """
    want = {(r["instance_id"], r["sigma"]): r["arms"]["spread_gp"] for r in stored}
    worst, n_checked = 0.0, 0
    for r in rows:
        if r["draw"] != 0:
            continue
        key = (r["instance_id"], r["sigma"])
        if key not in want:
            continue
        for rule in ("rule_a", "rule_c"):
            for n, got in r[rule].items():
                exp = want[key][rule][str(n)]
                delta = abs(float(got) - float(exp))
                n_checked += 1
                if delta > worst:
                    worst = delta
                if delta > GATE_TOL:
                    raise AssertionError(
                        f"draw 0 does not reproduce Q52 at instance {key[0]} "
                        f"sigma={key[1]} {rule} n={n}: {got:.15f} vs {exp:.15f} "
                        f"(|delta|={delta:.3e} > {GATE_TOL:g}). This script is not "
                        "running Q52's arm, so none of draws 1-4 describe it either.")
    return dict(n_checked=n_checked, worst_abs_delta=worst, tol=GATE_TOL)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def _arrival(curve: dict, target: float):
    return first_budget_to_target(curve, target=target, cap=CAP)


def _mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar on the discordant pairs. Q39's form, restated locally.

    ``b`` = arm-1-only hits, ``c`` = arm-2-only hits. With no discordant pairs the test
    is undefined and returns 1.0 — there is no evidence either way, which is not the
    same as evidence of no difference.
    """
    n = b + c
    if n == 0:
        return 1.0
    from scipy import stats
    return float(min(1.0, 2.0 * stats.binom.cdf(min(b, c), n, 0.5)))


def analyse(rows: list[dict], stored: list[dict]) -> dict:
    """Per-draw arrival, hit rates, and the verdict-stability count."""
    qlogei = {(r["instance_id"], r["sigma"]): r["arms"]["qlogei"] for r in stored}
    out = []
    for sigma in SIGMAS:
        for rule, targets in (("rule_c", TARGETS_RULE_C), ("rule_a", TARGETS_RULE_A)):
            for t in targets:
                per_draw = []
                for draw in range(N_DRAWS):
                    sub = [r for r in rows
                           if r["sigma"] == sigma and r["draw"] == draw]
                    if not sub:
                        continue
                    hits_s, hits_q, b, c = 0, 0, 0, 0
                    ev = []
                    for r in sub:
                        key = (r["instance_id"], r["sigma"])
                        if key not in qlogei or rule not in qlogei[key]:
                            continue
                        a_s = _arrival(r[rule], t)
                        a_q = _arrival(qlogei[key][rule], t)
                        s_hit = a_s is not ARRIVAL_CENSORED
                        q_hit = a_q is not ARRIVAL_CENSORED
                        hits_s += s_hit
                        hits_q += q_hit
                        b += s_hit and not q_hit
                        c += q_hit and not s_hit
                        if s_hit:
                            ev.append(int(a_s))
                    n_inst = len([r for r in sub
                                  if (r["instance_id"], r["sigma"]) in qlogei])
                    p = _mcnemar_exact(b, c)
                    per_draw.append(dict(
                        draw=draw, n=n_inst, hits_spread=hits_s, hits_qlogei=hits_q,
                        only_spread=b, only_qlogei=c, p=p,
                        median_evals=float(np.median(ev)) if ev else None,
                        differs=bool(p < 0.05)))
                if not per_draw:
                    continue
                hs = [d["hits_spread"] for d in per_draw]
                mean_h, sd_h = design_average(hs) if len(hs) > 1 else (float(hs[0]),
                                                                      float("nan"))
                n_differ = sum(d["differs"] for d in per_draw)
                out.append(dict(
                    sigma=sigma, rule=rule, target=t,
                    n=per_draw[0]["n"],
                    hits_qlogei=per_draw[0]["hits_qlogei"],
                    hits_spread_mean=mean_h, hits_spread_sd=sd_h,
                    hits_spread_min=int(min(hs)), hits_spread_max=int(max(hs)),
                    hits_spread_q52=hs[0] if per_draw[0]["draw"] == 0 else None,
                    n_draws_differ=n_differ, n_draws=len(per_draw),
                    stable=bool(n_differ == 0 or n_differ == len(per_draw)),
                    per_draw=per_draw))
    return dict(cells=out)


def report(analysis: dict) -> None:
    cells = analysis["cells"]
    print(f"\n{RULE}\n  HIT RATE ACROSS THE DESIGN LOTTERY — one-shot spread+GP vs "
          f"10-round qLogEI\n{RULE}")
    print(f"    {'sigma':>6}{'rule':>8}{'target':>8}{'qLogEI':>9}{'spread mean':>13}"
          f"{'sd':>7}{'range':>10}{'Q52 drew':>10}{'differs':>10}{'stable':>9}")
    for c in cells:
        rng = f"{c['hits_spread_min']}-{c['hits_spread_max']}"
        q52 = "—" if c["hits_spread_q52"] is None else str(c["hits_spread_q52"])
        print(f"    {c['sigma']:>6.2f}{c['rule'][-1].upper():>8}{c['target']:>8.2f}"
              f"{c['hits_qlogei']:>6}/{c['n']:<2}"
              f"{c['hits_spread_mean']:>13.1f}{c['hits_spread_sd']:>7.2f}{rng:>10}"
              f"{q52:>10}"
              f"{c['n_draws_differ']:>7}/{c['n_draws']:<2}"
              f"{'yes' if c['stable'] else 'NO':>9}")
    unstable = [c for c in cells if not c["stable"]]
    print(f"\n    'differs' = draws where McNemar p<0.05 against qLogEI on the same "
          f"instances.")
    print(f"    'stable'  = all five draws agree on the verdict. {len(cells)-len(unstable)}"
          f" of {len(cells)} cells stable.")
    if unstable:
        print(f"\n    VERDICT FLIPS WITH THE DRAW in {len(unstable)} cells:")
        for c in unstable:
            print(f"      sigma={c['sigma']} rule {c['rule'][-1].upper()} "
                  f"target {c['target']:.2f}: {c['n_draws_differ']} of {c['n_draws']} "
                  f"draws call it a difference")
        print("\n    Those cells are a property of which Latin hypercube was drawn, not "
              "of the method.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_instances", nargs="?", type=int, default=N_INSTANCES)
    ap.add_argument("--gate-only", action="store_true",
                    help="run draw 0 only, check it against Q52, and stop")
    ap.add_argument("--time-one", action="store_true",
                    help="run a single instance-cell-draw and print the time")
    args = ap.parse_args()

    stored = json.loads(Q52.read_text())["rows"]
    print(f"{RULE}\nQ54 — Hill spread+GP at {N_DRAWS} design draws\n{RULE}")
    print(f"  d={DIM}, sigma in {SIGMAS}, {args.n_instances} instances, cap {CAP}")
    print(f"  checkpoints {CHECKPOINTS}")
    print(f"  draw 0 = Q52's own seed; gated against {Q52.name} at {GATE_TOL:g}")
    print(f"  qLogEI is READ from {Q52.name}, never re-run — the contrast stays paired\n")

    ensemble = load_ensemble(dim=DIM)[:args.n_instances]

    if args.time_one:
        t = time.time()
        one_draw(ensemble[0], SIGMAS[0], 1)
        secs = time.time() - t
        total = secs * args.n_instances * len(SIGMAS) * N_DRAWS
        print(f"  one instance-cell-draw: {secs:.1f}s")
        print(f"  full grid = {args.n_instances} x {len(SIGMAS)} x {N_DRAWS} = "
              f"{args.n_instances*len(SIGMAS)*N_DRAWS} units ~ {total/60:.0f} min "
              "single-core")
        return

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["instance_id"], r["sigma"], r["draw"]) for r in done}
    draws = [0] if args.gate_only else list(range(N_DRAWS))
    todo = [(inst, s, d) for d in draws for s in SIGMAS for inst in ensemble
            if (inst.instance_id, s, d) not in have]
    if have:
        print(f"  resuming — {len(have)} units already on disk")
    print(f"  {len(todo)} units to run\n")

    t0 = time.time()
    for k, (inst, sigma, draw) in enumerate(todo, 1):
        t = time.time()
        res = one_draw(inst, sigma, draw)
        done.append(dict(instance_id=inst.instance_id, sigma=sigma, draw=draw,
                         secs=round(time.time() - t, 1), **res))
        OUT.write_text(json.dumps(dict(provenance=_provenance(args), rows=done), indent=1))
        if k % 5 == 0 or k == len(todo):
            el = time.time() - t0
            print(f"    {k:>4}/{len(todo)}  {el/60:>5.1f} min elapsed, "
                  f"~{el/k*(len(todo)-k)/60:>5.1f} min left", flush=True)

    gate = gate_draw_zero(done, stored)
    print(f"\n  DRAW-0 GATE PASSED — {gate['n_checked']} stored values reproduced, "
          f"worst |delta| = {gate['worst_abs_delta']:.3e}")
    if args.gate_only:
        return

    analysis = analyse(done, stored)
    report(analysis)
    OUT.write_text(json.dumps(dict(provenance=_provenance(args), gate=gate,
                                   analysis=analysis, rows=done), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.0f} min)")


if __name__ == "__main__":
    main()
