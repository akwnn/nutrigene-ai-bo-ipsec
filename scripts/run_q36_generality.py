"""Q36 / T2.1 — does the rule A / rule C reversal survive off the Hill oracle?

    python scripts/run_q36_generality.py

THE GAP THIS CLOSES
-------------------
Every headline number in this project comes from one landscape family, which Q22
measured as ~93% additive and which is coordinate-wise unimodal by construction. A
finding about *scoring conventions* should not care about that. A finding about *this
oracle* would. Until it is run on something else, the two are indistinguishable.

Hartmann6 is the standard answer: 6-D, deceptive, six local optima, genuinely
non-additive, and already behind the same `Oracle` ABC. Ackley is the needle-in-a-
haystack case where BO can legitimately lose. Both are posed as maximisation on coded
[0,1]^6 in `oracles.py`, so the arms, the budget and the noise transfer unchanged.

DECISION RULE, fixed here before the run
----------------------------------------
    reversal reproduces on BOTH      -> the finding is about scoring conventions, not
                                        about the Hill oracle. A materially larger claim.
    reproduces on NEITHER            -> the finding is family-specific and the paper
                                        must say so in those words.
    reproduces on one but not other  -> report both; do not round it to either story.

"Reproduces" means: DoE beats BO under rule A, and BO beats DoE under rule C, with each
paired 95% CI excluding zero -- the same pattern E2 shows at d=6 sigma=0.25.

WHAT COUNTS AS AN INDEPENDENT REPLICATE HERE
--------------------------------------------
Hartmann6 and Ackley are single functions, not ensembles, so the clustering unit that
was "landscape" in E2 becomes "seed". 25 seeds, matched to E2's n=25, and inference is
paired across them. Calling 25 seeds on one function "n=25 landscapes" would be the
pseudo-replication this project criticises the source paper for, so it is not claimed.

RULE C IS REPORTED IN BOTH FORMS, because Q35 showed it has to be
------------------------------------------------------------------
Q35 measured that the DoE arm's rule-C score moves by +0.2995 depending on whether its
argmax is constrained to the region actually explored -- more than the entire rule-C gap
it was used to demonstrate. Reporting only the unconstrained form here would repeat that
strawman on a fresh dataset.
"""

from __future__ import annotations

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

from scipy.stats import wilcoxon                                    # noqa: E402

from boec.campaign import Campaign, CampaignConfig                  # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                    # noqa: E402
from boec.metrics import constrained_argmax                         # noqa: E402
from boec.oracles import Ackley, Hartmann6                          # noqa: E402
from boec.rsm import fit_second_order                               # noqa: E402
from boec.torch_oracle import TorchEvaluator                        # noqa: E402

BUDGET = 48
N_SEEDS = 25
SIGMA_REL = 0.25          # matched to E2's primary cell
N_RESTARTS = 20
RAW_SAMPLES = 4096
RULE = "=" * 96


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def run_function(oracle) -> list[dict]:
    d = oracle.dim
    bounds = _bounds(d)
    opt = float(oracle.optimum_value)
    rows = []
    for seed in range(N_SEEDS):
        # ---- BO arm --------------------------------------------------------
        ev = TorchEvaluator(oracle, sigma_rel=SIGMA_REL, seed=seed)
        c = Campaign(ev, bounds, CampaignConfig(d=d, budget=BUDGET, q=4, seed=seed)).run()
        bo_a = opt - float(reported_best_curve(ev.truth(c.train_X), c.train_Y)[-1])

        model = c.fit()

        def gp_mean(Z: torch.Tensor) -> torch.Tensor:
            with torch.no_grad():
                return model.posterior(Z).mean

        x_bo, _, _ = constrained_argmax(gp_mean, bounds, n_restarts=N_RESTARTS,
                                        raw_samples=RAW_SAMPLES, seed=seed)
        bo_c = opt - float(ev.truth(x_bo.reshape(1, -1)))

        # ---- DoE arm -------------------------------------------------------
        ed = TorchEvaluator(oracle, sigma_rel=SIGMA_REL, seed=seed)
        r = run_doe_arm(ed, bounds, truth=ed.truth, budget=BUDGET, seed=seed)
        doe_a = opt - float(r.curve_true[-1])
        doe_c = opt - float(ed.truth(r.confirmation_x.unsqueeze(0)))

        # the constrained variant, for the reason in the module docstring
        kept = list(r.kept_factors)
        s2 = slice(r.n_stage1, r.n_stage1 + r.n_stage2)
        fit = fit_second_order(r.X_visited[s2][:, kept], r.Y_visited[s2])
        x_con, _, _ = constrained_argmax(fit.predict, r.stage2_bounds,
                                         n_restarts=N_RESTARTS,
                                         raw_samples=RAW_SAMPLES, seed=seed)
        full = torch.tensor([r.dropped_held_at.get(i, 0.0) for i in range(d)],
                            dtype=torch.double)
        full[kept] = x_con.double().reshape(-1)
        doe_c_con = opt - float(ed.truth(full.unsqueeze(0)))

        # Does the design contain the answer? A centre run sits at 0.5 in every
        # coordinate, so any oracle whose optimum is the box centre is scored on a
        # point the DoE arm measures for free. Ackley is exactly that case.
        ox = oracle.optimum_x
        centred = ox is not None and bool(np.allclose(np.asarray(ox), 0.5, atol=1e-9))

        rows.append(dict(function=oracle.name, seed=seed,
                         bo_a=bo_a, bo_c=bo_c, doe_a=doe_a,
                         doe_c_unconstrained=doe_c, doe_c_constrained=doe_c_con,
                         stationary_kind=r.stationary_kind,
                         optimum_at_design_centre=centred,
                         confirmation_inside_stage2=bool(r.confirmation_inside_stage2)))
    return rows


def _paired(rows, a: str, b: str) -> tuple[float, float, float, float]:
    d = np.array([r[a] for r in rows]) - np.array([r[b] for r in rows])
    m, lo, hi = instance_bootstrap(d, n_boot=2000)
    try:
        p = wilcoxon(d).pvalue
    except ValueError:
        p = float("nan")
    return m, lo, hi, p


def report(rows, name: str) -> dict:
    print(f"\n{RULE}\nQ36 · {name} · {N_SEEDS} seeds · sigma_rel={SIGMA_REL} · "
          f"budget={BUDGET}\n{RULE}")
    print(f"{'arm / rule':<44}{'mean regret':>13}{'median':>10}")
    for key, label in (("bo_a", "BO   rule A  (best observed)"),
                       ("doe_a", "DoE  rule A  (best observed)"),
                       ("bo_c", "BO   rule C  (GP posterior-mean argmax)"),
                       ("doe_c_unconstrained", "DoE  rule C  UNCONSTRAINED"),
                       ("doe_c_constrained", "DoE  rule C  CONSTRAINED")):
        v = np.array([r[key] for r in rows])
        print(f"{label:<44}{v.mean():>13.4f}{np.median(v):>10.4f}")

    out = {}
    print(f"\n  {'contrast':<44}{'DoE - BO  (>0 = BO better)':>44}")
    for a, b, tag in (("doe_a", "bo_a", "rule A"),
                      ("doe_c_unconstrained", "bo_c", "rule C, DoE unconstrained"),
                      ("doe_c_constrained", "bo_c", "rule C, DoE constrained")):
        m, lo, hi, p = _paired(rows, a, b)
        verdict = "BO better" if lo > 0 else ("DoE better" if hi < 0 else "null")
        out[tag] = dict(diff=m, lo=lo, hi=hi, p=p, verdict=verdict)
        print(f"  {tag:<44}{m:>+9.4f} [{lo:>+8.4f},{hi:>+8.4f}] p={p:<8.4f} {verdict}")

    kinds = {}
    for r in rows:
        kinds[r["stationary_kind"]] = kinds.get(r["stationary_kind"], 0) + 1
    esc = sum(1 for r in rows if not r["confirmation_inside_stage2"])
    print(f"\n  fitted-surface stationary point: {kinds}")
    print(f"  predicted optimum outside the stage-2 region: {esc}/{len(rows)}")

    if rows[0].get("optimum_at_design_centre"):
        print("\n  *** CONFOUND — READ BEFORE QUOTING THE RULE-A ROW ***\n"
              "  This function's optimum sits at the exact centre of the coded box, and\n"
              "  every screening and CCD design in the DoE arm includes CENTRE RUNS. The\n"
              "  DoE design therefore CONTAINS THE ANSWER by construction, and its rule-A\n"
              "  regret is ~0 for a reason that has nothing to do with sequential DoE\n"
              "  being a good search strategy. The rule-A comparison is void here; the\n"
              "  rule-C comparison still means something, because it asks what the fitted\n"
              "  SURFACE recommends rather than what the design happened to contain.")

    a_doe_better = out["rule A"]["verdict"] == "DoE better"
    c_bo_better = out["rule C, DoE unconstrained"]["verdict"] == "BO better"
    print(f"\n  REVERSAL REPRODUCES (DoE wins rule A, BO wins rule C): "
          f"{'YES' if (a_doe_better and c_bo_better) else 'NO'}"
          f"   [rule A: {out['rule A']['verdict']}, "
          f"rule C: {out['rule C, DoE unconstrained']['verdict']}]")
    return out


def main() -> None:
    everything, verdicts, t0 = [], {}, time.time()
    for oracle in (Hartmann6(), Ackley(dim=6)):
        rows = run_function(oracle)
        everything.extend(rows)
        verdicts[oracle.name] = report(rows, oracle.name)
        print(f"\n  [{time.time() - t0:.0f}s elapsed]", flush=True)

    out = ROOT / "results" / "q36-generality.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(dict(rows=everything, verdicts=verdicts), indent=1))
    print(f"\n  written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
