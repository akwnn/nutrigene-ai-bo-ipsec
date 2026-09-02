"""Q49 — the noise threshold curve: above what CV does buying more assays stop helping?

    python scripts/run_q49_noise_threshold.py   # log at results/q49-noise-threshold.log

THE ITEM THIS CLOSES
--------------------
Every close-out list has carried "the noise threshold curve" as outstanding, and Q47's
§6 tries to pair its correlation floor with a noise ceiling stated as *"above CV ≈ X, no
method finds anything within budget."* **No such curve existed.** What existed was
held-out surrogate R² at two noise levels — 0.106 at σ_rel=0.25, 0.744 at 0.10
(`results/bench-surrogate.log`) — which is a statement about how well a model can be
*fitted*, not about what an experimenter walks away with.

FOUND WHILE VALIDATING SOMETHING ELSE
--------------------------------------
Q47's under-budget control spends 32 expensive assays instead of 48. At d=6 σ_rel=0.10
it scored **better** than the 48-point arm under rule A. Chasing that produced the
curve below, so this script exists because a control arm disagreed with expectation.

THE MEASUREMENT, AND WHY IT SPLITS INTO TWO
--------------------------------------------
A space-filling design of `n` points, scored two ways:

* **oracle-best** — the best TRUE value among the points visited. What the design
  *found*. Monotone in `n` by construction: more points cannot make the best one worse.
* **rule A / reported-best** — the true value of the point chosen by the best
  *observation*. What the experimenter actually walks away with, and this project's
  registered scoring rule (`diagnostics.reported_best_curve`).

**The gap between them is the noise ceiling, in units anyone can act on.** Where
oracle-best keeps improving and reported-best does not, the assays are finding better
recipes that the readout cannot identify — and buying more of them is waste.

No GP anywhere. Design, evaluate, score. Seconds.

⚠️ σ_rel ABOVE 0.25 IS OUTSIDE THE ENSEMBLE'S DESIGN RANGE. The acceptance floor was
calibrated so a true depth of ~0.11 clears 3σ/√48 at σ_rel=0.25 (Phase A2). Points at
0.35 and 0.50 are reported because "the landscape is no longer detectable at this CV"
is the answer to the question, but they describe instances built for a quieter assay.
"""

from __future__ import annotations

import json
import os
import sys
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

from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.optimizers import lhs_design                             # noqa: E402
from boec.oracles import load_ensemble                             # noqa: E402
from boec.torch_oracle import BiphasicOracle                       # noqa: E402

N_INSTANCES, SEEDS = 25, (0, 1)
NS = (8, 16, 24, 32, 48, 64, 96, 128, 192)
SIGMAS = (0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50)
DIMS = (6, 8)
BASE_N = 48                       # the project's budget, the reference column
RULE = "=" * 108


def _seed_of(instance_id: str, seed: int, salt: int) -> int:
    return (int(instance_id[:8], 16) * 1000 + seed * 7 + salt) % (2**31 - 1)


def sweep(dim: int, sigma: float) -> dict[int, dict[str, np.ndarray]]:
    """Per-instance mean regret at each n, under both scoring rules."""
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    ens = load_ensemble(dim=dim)[:N_INSTANCES]
    out: dict[int, dict[str, np.ndarray]] = {}
    for n in NS:
        rep, orc = [], []
        for inst in ens:
            r, o_ = [], []
            for s in SEEDS:
                # design seeded per (instance, seed) -- Q48: a shared design leaves the
                # design component of variance out of every interval computed from these
                X = lhs_design(bounds, n, seed=_seed_of(inst.instance_id, s, 2))
                orac = BiphasicOracle(inst, sigma_rel=sigma, seed=s)
                Y, _ = orac.evaluate(X)
                T = orac.truth(X)
                opt = float(inst.optimum_value)
                r.append(opt - float(reported_best_curve(T, Y)[-1]))
                o_.append(opt - float(T.max()))
            rep.append(np.mean(r))
            orc.append(np.mean(o_))
        out[n] = dict(reported=np.array(rep), oracle=np.array(orc))
    return out


def contrast(a: np.ndarray, b: np.ndarray) -> dict:
    """b - a, paired at instance level. Positive means `a` has the lower regret."""
    d = np.asarray(b) - np.asarray(a)
    m, lo, hi = instance_bootstrap(d, n_boot=4000)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:
        p = float("nan")
    return dict(diff=float(m), lo=float(lo), hi=float(hi), p=p,
                verdict="helps" if lo > 0 else ("hurts" if hi < 0 else "null"))


def main() -> None:
    out = []
    print(f"{RULE}\nQ49 — the noise threshold curve. Does buying more assays help, and "
          f"at what CV does it stop?\n{RULE}")
    print("  oracle-best = the best TRUE value among the points visited (what the design "
          "found)\n  reported    = the true value of the observed argmax (what you walk "
          "away with; rule A)\n")
    for dim in DIMS:
        for sigma in SIGMAS:
            s = sweep(dim, sigma)
            flag = "  [outside the ensemble's design range]" if sigma > 0.25 else ""
            print(f"\n  d={dim}  sigma_rel={sigma}{flag}")
            print(f"    {'n assays':>9}" + "".join(f"{n:>9}" for n in NS))
            print(f"    {'oracle':>9}" +
                  "".join(f"{s[n]['oracle'].mean():>9.4f}" for n in NS))
            print(f"    {'reported':>9}" +
                  "".join(f"{s[n]['reported'].mean():>9.4f}" for n in NS))
            # does quadrupling the budget help, under each rule?
            for rule in ("oracle", "reported"):
                c4 = contrast(s[192][rule], s[48][rule])
                c2 = contrast(s[96][rule], s[48][rule])
                print(f"      {rule:<9} 48 ->  96: {c2['diff']:>+8.4f} "
                      f"[{c2['lo']:>+7.4f},{c2['hi']:>+7.4f}] {c2['verdict']:<6}"
                      f"   48 -> 192: {c4['diff']:>+8.4f} "
                      f"[{c4['lo']:>+7.4f},{c4['hi']:>+7.4f}] {c4['verdict']}")
            gap = s[192]["reported"].mean() - s[192]["oracle"].mean()
            print(f"      identification gap at n=192: {gap:+.4f}  "
                  f"({100 * gap / max(s[192]['reported'].mean(), 1e-9):.0f}% of what the "
                  f"experimenter is left with is failure to identify, not failure to find)")
            out.append(dict(dim=dim, sigma=sigma,
                            n=list(NS),
                            oracle=[float(s[n]["oracle"].mean()) for n in NS],
                            reported=[float(s[n]["reported"].mean()) for n in NS],
                            quadruple={r: contrast(s[192][r], s[48][r])
                                       for r in ("oracle", "reported")},
                            double={r: contrast(s[96][r], s[48][r])
                                    for r in ("oracle", "reported")}))
    (ROOT / "results" / "q49-noise-threshold.json").write_text(json.dumps(out, indent=1))
    print(f"\n{RULE}\n  THE THRESHOLD IS WHERE THE 'reported' ROW GOES FLAT WHILE "
          f"'oracle' KEEPS FALLING.\n  Past it the assays are finding better recipes "
          f"than the readout can identify, and\n  buying more of them is waste.\n{RULE}")


if __name__ == "__main__":
    main()
