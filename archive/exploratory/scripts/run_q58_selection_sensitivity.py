"""Q58 — is the classical arm's lead an artefact of one selection rule? Workstream 6.

    python scripts/run_q58_selection_sensitivity.py [n_instances] [--workers 3]

THE QUESTION
------------
Every headline in this project scores a campaign at the **single noisy readout**. Q55 then
showed that rule is bad: across both arms and all four cells, the noisy argmax is the
genuinely best visited well only 2–18% of the time, and the adaptive arm suffers more
because it clusters its wells where differences are smaller than the noise.

That opens an obvious objection. If the classical arm wins at the higher-noise condition
only because the adaptive arm is being punished by a lottery among near-ties, then the
result is about **one selection convention**, not about design geometry — and a lab that
replicates, confirms its shortlist, or trusts a model would see no such advantage.

This run settles it at the primary cell by re-selecting from *the same campaigns* under
four rules (:data:`boec.selection.SELECTION_RULES`) and re-scoring each.

WHAT IS HELD FIXED, AND WHAT IS NOT
-------------------------------------
The campaigns are identical across rules — same seeds, same wells, same order. **Only the
final pick moves.** That is what makes this a clean sensitivity analysis rather than four
different experiments.

The rules are **not budget-matched to each other**, deliberately: replicating costs a
further ``n`` wells and confirming the top three costs three. The question is not which arm
wins at 48 wells under each rule, it is whether the reported advantage survives a lab that
spends a little more to choose more carefully. The cost of each rule is reported beside it.

WHAT WOULD FALSIFY THE HEADLINE
---------------------------------
If the classical arm's advantage shrinks toward zero as the selection rule improves, the
published result is largely a selection artefact and must be restated. If it holds under
all four, it is a statement about where the campaigns looked. Registered before the run;
neither outcome is pre-written.
"""

from __future__ import annotations

import argparse
import json
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

from boec.campaign import Campaign, CampaignConfig                    # noqa: E402
from boec.diagnostics import instance_bootstrap                       # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.selection import (SELECTION_RULES, mean_of_replicates,      # noqa: E402
                            posterior_mean_at_visited, single_readout, top_k_confirm)
from boec.surrogate import build_gp                                   # noqa: E402
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar           # noqa: E402

DIM, BUDGET, Q = 6, 48, 4
#: The primary cell. Full n there beats small n everywhere: this is the one cell whose
#: number the objection is actually about.
SIGMA = 0.25
N_INSTANCES, N_SEEDS = 25, 2
TOP_K = 3
N_BOOT = 4000

#: Extra wells each rule costs beyond the 48-well campaign. Reported, never netted off.
RULE_COST = {"single": 0, "replicate": BUDGET, "top3": TOP_K, "posterior": 0}

OUT = ROOT / "results" / "q58-selection-sensitivity.json"
RULE = "=" * 100


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(DIM, dtype=torch.double),
                        torch.ones(DIM, dtype=torch.double)])


def _yvar(Y: torch.Tensor, orac) -> torch.Tensor:
    """The observation variance the arm's own evaluator would report for ``Y``.

    `run_doe_arm` returns its readings but discards the variances, and `build_gp`
    requires them. Recomputing with :func:`boec.torch_oracle._plug_in_yvar` — the single
    definition both evaluator classes use — keeps the posterior-mean rule fitted on the
    same noise model the campaign was run under. Substituting a homoscedastic guess here
    would make this rule's row a statement about a different surrogate.
    """
    v = _plug_in_yvar(Y.double().numpy(), orac.sigma_rel, orac.sigma_add)
    return torch.from_numpy(v)


def _pick_all(X, Y, V, Y2, Yc, truth, opt: float) -> dict:
    """Regret under each registered selection rule, from one campaign's visit log.

    ``Y2`` and ``Yc`` are independent re-measurements of the same wells — the oracle draws
    fresh noise on every call, so these are genuine replicates rather than the same
    numbers twice.
    """
    t = truth(X).double().reshape(-1)
    picks = {
        "single": single_readout(Y),
        "replicate": mean_of_replicates(Y, Y2),
        "top3": top_k_confirm(Y, Yc, k=TOP_K),
    }
    model = build_gp(X, Y, V, _bounds())

    def mean(Z, _m=model):
        with torch.no_grad():
            return _m.posterior(Z).mean

    picks["posterior"] = posterior_mean_at_visited(mean, X)
    # The ceiling every rule is chasing: the best well actually visited.
    best = float(t.max())
    return {k: opt - float(t[i]) for k, i in picks.items()} | {
        "oracle_best": opt - best,
        "hit": {k: bool(abs(float(t[i]) - best) < 1e-12) for k, i in picks.items()},
    }


def one(job: tuple[int, int]) -> dict:
    """One landscape x one seed: both arms, all four selection rules."""
    idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM)[idx]
    opt = float(inst.optimum_value)
    b = _bounds()
    out: dict = {}

    # --- adaptive arm ---------------------------------------------------------
    o = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    camp = Campaign(o, b, CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=seed,
                                         acq=AcqConfig(kind="qlogei")))
    camp.run()
    X = camp.train_X
    Y2, _ = o.evaluate(X)          # a second independent reading of every well
    Yc, _ = o.evaluate(X)          # and a third, for the confirmation protocol
    out["bo"] = _pick_all(X, camp.train_Y, camp.train_Yvar, Y2, Yc, o.truth, opt)

    # --- classical arm --------------------------------------------------------
    od = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    r = run_doe_arm(od, b, truth=od.truth, budget=BUDGET, seed=seed)
    Xd = r.X_visited
    Y2d, _ = od.evaluate(Xd)
    Ycd, _ = od.evaluate(Xd)
    out["doe"] = _pick_all(Xd, r.Y_visited, _yvar(r.Y_visited, od), Y2d, Ycd,
                           od.truth, opt)

    return dict(instance=inst.instance_id, instance_index=idx, seed=seed,
                sigma=SIGMA, secs=round(time.time() - t0, 1), arms=out)


def _per_instance(rows: list[dict], arm: str, key: str) -> np.ndarray:
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["instance"], []).append(r["arms"][arm][key])
    return np.array([float(np.mean(v)) for _, v in sorted(by.items())])


def analyse(rows: list[dict]) -> dict:
    from scipy import stats
    out = []
    for rule in SELECTION_RULES:
        bo = _per_instance(rows, "bo", rule)
        doe = _per_instance(rows, "doe", rule)
        d = doe - bo
        m, lo, hi = instance_bootstrap(d, n_boot=N_BOOT)
        w = stats.wilcoxon(d) if np.any(d != 0) else None
        out.append(dict(
            rule=rule, extra_wells=RULE_COST[rule], n=int(d.size),
            bo=float(bo.mean()), doe=float(doe.mean()),
            contrast=float(m), lo=float(lo), hi=float(hi),
            wilcoxon_p=float(w.pvalue) if w is not None else 1.0,
            significant=bool(hi < 0 or lo > 0),
            bo_hit=float(np.mean([r["arms"]["bo"]["hit"][rule] for r in rows])),
            doe_hit=float(np.mean([r["arms"]["doe"]["hit"][rule] for r in rows]))))
    ceiling = dict(bo=float(_per_instance(rows, "bo", "oracle_best").mean()),
                   doe=float(_per_instance(rows, "doe", "oracle_best").mean()))
    return dict(rules=out, ceiling=ceiling)


def report(a: dict) -> None:
    print(f"\n{RULE}\n  THE CLASSICAL ARM'S LEAD UNDER FOUR SELECTION RULES  "
          f"(d={DIM}, sigma={SIGMA}, n=25)\n{RULE}")
    print(f"    {'rule':>11}{'extra wells':>13}{'BO':>9}{'DoE':>9}"
          f"{'DoE - BO':>26}{'p':>9}{'BO picks best':>15}{'DoE picks best':>16}")
    for r in a["rules"]:
        star = "*" if r["significant"] else " "
        print(f"    {r['rule']:>11}{r['extra_wells']:>13}{r['bo']:>9.4f}{r['doe']:>9.4f}"
              f"{r['contrast']:>+13.4f} [{r['lo']:>+.4f},{r['hi']:>+.4f}]{star}"
              f"{r['wilcoxon_p']:>8.4f}"
              f"{100*r['bo_hit']:>14.0f}%{100*r['doe_hit']:>15.0f}%")
    print(f"\n    ceiling (best well actually visited): BO {a['ceiling']['bo']:.4f}, "
          f"DoE {a['ceiling']['doe']:.4f}")
    print("    'picks best' = how often the rule lands on that campaign's genuinely best "
          "visited well.")
    print("    * = bootstrap interval excludes zero. Extra wells are NOT netted off; each "
          "rule costs what it costs.")

    base = next(r for r in a["rules"] if r["rule"] == "single")
    print(f"\n{RULE}\n  DOES THE PUBLISHED ADVANTAGE SURVIVE A BETTER SELECTION RULE?"
          f"\n{RULE}")
    print(f"    Published rule ('single'): {base['contrast']:+.4f} "
          f"[{base['lo']:+.4f}, {base['hi']:+.4f}]")
    surviving = [r for r in a["rules"] if r["rule"] != "single" and r["significant"]
                 and np.sign(r["contrast"]) == np.sign(base["contrast"])]
    print(f"    Same direction AND significant under {len(surviving)} of "
          f"{len(a['rules']) - 1} alternatives: "
          f"{', '.join(r['rule'] for r in surviving) or 'none'}")
    shrink = [(r["rule"], r["contrast"] / base["contrast"]) for r in a["rules"]
              if r["rule"] != "single" and base["contrast"] != 0]
    print("    magnitude relative to the published rule: "
          + ", ".join(f"{n} {v:.2f}x" for n, v in shrink))
    if len(surviving) == len(a["rules"]) - 1:
        print("\n    The advantage is NOT an artefact of single-readout selection. It")
        print("    holds under replication, confirmation and a model-based pick.")
    elif not surviving:
        print("\n    The advantage DISAPPEARS under every better selection rule. The")
        print("    published result is a statement about one convention, and must be")
        print("    restated as such.")
    else:
        print("\n    The advantage is PARTIALLY selection-dependent. Report which rules")
        print("    it survives and which it does not — do not report only the survivors.")


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return dict(git_sha=_git("rev-parse", "HEAD"),
                git_dirty=bool(_git("status", "--porcelain")),
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), argv=list(argv),
                python=platform.python_version(), torch=torch.__version__,
                botorch=botorch.__version__, gpytorch=gpytorch.__version__,
                numpy=np.__version__, scipy=scipy.__version__,
                config=dict(dim=DIM, sigma=SIGMA, budget=BUDGET, q=Q, top_k=TOP_K,
                            n_instances=N_INSTANCES, n_seeds=N_SEEDS,
                            rules=list(SELECTION_RULES), rule_cost=RULE_COST,
                            n_boot=N_BOOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_instances", nargs="?", type=int, default=N_INSTANCES)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    print(f"{RULE}\nQ58 — selection-rule sensitivity at the primary cell\n{RULE}")
    print(f"  d={DIM}, sigma={SIGMA}, {args.n_instances} landscapes x {N_SEEDS} seeds, "
          f"budget {BUDGET}")
    print(f"  rules {SELECTION_RULES}; extra wells {RULE_COST}")
    print("  campaigns are identical across rules — only the final pick moves\n")

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["instance_index"], r["seed"]) for r in done}
    todo = [(i, s) for s in range(N_SEEDS) for i in range(args.n_instances)
            if (i, s) not in have]
    if have:
        print(f"  resuming — {len(have)} campaigns on disk")
    print(f"  {len(todo)} to run on {args.workers} workers\n")

    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, row in enumerate(pool.map(one, todo), 1):
                done.append(row)
                OUT.write_text(json.dumps(
                    dict(provenance=_provenance(sys.argv), rows=done), indent=1))
                if k % 5 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f"    {k:>4}/{len(todo)}  {el/60:>5.1f} min, "
                          f"~{el/k*(len(todo)-k)/60:>5.1f} min left", flush=True)

    a = analyse(done)
    report(a)
    OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv), analysis=a,
                                   rows=done), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
