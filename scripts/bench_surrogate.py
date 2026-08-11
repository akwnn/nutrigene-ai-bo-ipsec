"""How accurate is the surrogate, and which code changes actually improve it?

Reproduce with `python scripts/bench_surrogate.py`; log at
`results/bench-surrogate.log`.

------------------------------------------------------------------------------
WHY THIS IS SEPARATE FROM EVERY OTHER SCRIPT HERE
------------------------------------------------------------------------------

This measures **model accuracy**, not method performance. It fits candidate
surrogates on the same points and scores them against held-out truth. There is
no acquisition function, no campaign, no regret, and no baseline being competed
against.

That distinction is what makes it usable without a pre-registration. `e2.yaml`
registers `no_per_method_tuning: true` to stop the BO arm being improved against
frozen baselines after seeing it lose -- a rule about *comparisons*. "Does this
kernel predict held-out truth better" is not a comparison between methods; it is
a property of a model, checkable by anyone, and it cannot be gamed by choosing a
favourable comparator because there is no comparator.

**What it therefore CANNOT tell you: whether better accuracy buys better
regret.** Those come apart, and on this benchmark there is direct evidence that
they do -- Q26 found a cell where the surrogate learned nothing extra and regret
improved anyway, and another where discrimination improved sharply and regret
did not move. Any claim from this bench stops at "the model fits better".

------------------------------------------------------------------------------
THE SCORE
------------------------------------------------------------------------------

Held-out R2 against NOISELESS truth on uniform draws over the whole cube. Not
against noisy observations -- at sigma_rel 0.25 the noise ceiling would dominate
and every model would score about the same for the wrong reason.

Also reported:
  * RMSE, because R2 near zero is hard to read;
  * calibration -- the share of held-out points inside the model's own 95%
    interval, which should be 0.95. A model that fits better and lies about its
    confidence is not an improvement for BO, since the acquisition consumes the
    variance and not just the mean;
  * relevance -- the share of the model's weight landing on the genuinely
    active factors, chance being n_active / d.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boec.optimizers import sobol_design                # noqa: E402
from boec.oracles import load_ensemble                  # noqa: E402
from boec.surrogate import (                            # noqa: E402
    build_gp, component_variances, lengthscales, predictive,
)
from boec.torch_oracle import BiphasicOracle            # noqa: E402

OUT = Path("results/bench-surrogate.json")

N_INSTANCES = 10
SEEDS = (0, 1)
N_TEST = 800
SIGMAS = (0.25, 0.10)
NS = (14, 30, 46)

#: Every candidate is a kwargs dict for `build_gp`. The first is what E2 ran and
#: is the reference every other row is read against.
CANDIDATES: list[tuple[str, dict]] = [
    ("product (E2)",        dict()),
    ("+ warp",              dict(input_warping=True)),
    ("+ restarts x4",       dict(fit_restarts=4)),
    ("additive",            dict(kernel_structure="additive")),
    ("add+int",             dict(kernel_structure="additive+interaction")),
    ("add+int + warp",      dict(kernel_structure="additive+interaction",
                                 input_warping=True)),
    ("add+int + restarts",  dict(kernel_structure="additive+interaction",
                                 fit_restarts=4)),
]


def score_one(inst, sigma, seed, n, kw, Xte, d):
    """Fit one candidate on n points and score it on held-out truth."""
    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    X = sobol_design(bounds, n, seed=seed)
    Y, Yvar = o.evaluate(X)
    m = build_gp(X, Y, Yvar, bounds, **kw)

    truth = o.truth(Xte).reshape(-1).double()
    with torch.no_grad():
        p = predictive(m, Xte, noise=None)
        mean = p.mean.reshape(-1).double()
        lo, hi = p.interval(alpha=0.05)
        lo, hi = lo.reshape(-1).double(), hi.reshape(-1).double()
        act = list(inst.active_idx)
        if kw.get("kernel_structure", "product") == "product":
            w = (1.0 / lengthscales(m).reshape(-1)).double()
        else:
            w = component_variances(m).double()
    resid = mean - truth
    return dict(
        r2=1 - float(resid.var()) / float(truth.var()),
        rmse=float(resid.pow(2).mean().sqrt()),
        coverage=float(((truth >= lo) & (truth <= hi)).double().mean()),
        relevance=float(w[act].sum() / w.sum()),
    )


def main() -> None:
    rng = np.random.default_rng(0)
    rows = []
    for d in (6, 8):
        ens = load_ensemble(dim=d)[:N_INSTANCES]
        Xte = torch.from_numpy(rng.uniform(size=(N_TEST, d)))
        chance = len(ens[0].active_idx) / d
        for sigma in SIGMAS:
            print(f"\n{'=' * 92}\nd={d} · sigma_rel={sigma} · {N_INSTANCES} "
                  f"instances x {len(SEEDS)} seeds · held-out R2 vs NOISELESS truth"
                  f"\n{'=' * 92}")
            print(f"{'surrogate':>20} " + "".join(f"{'R2@'+str(n):>9}" for n in NS)
                  + "".join(f"{'cover@'+str(n):>11}" for n in NS)
                  + f"{'relev@46':>10}")
            for name, kw in CANDIDATES:
                agg = {n: [] for n in NS}
                for n in NS:
                    for inst in ens:
                        for seed in SEEDS:
                            try:
                                agg[n].append(score_one(inst, sigma, seed, n, kw,
                                                        Xte, d))
                            except Exception as e:          # noqa: BLE001
                                agg[n].append(dict(r2=float("nan"),
                                                   rmse=float("nan"),
                                                   coverage=float("nan"),
                                                   relevance=float("nan")))
                                print(f"    ! {name} n={n}: {type(e).__name__}")
                mean = {n: {k: float(np.nanmean([a[k] for a in agg[n]]))
                            for k in ("r2", "rmse", "coverage", "relevance")}
                        for n in NS}
                print(f"{name:>20} "
                      + "".join(f"{mean[n]['r2']:>9.3f}" for n in NS)
                      + "".join(f"{mean[n]['coverage']:>11.3f}" for n in NS)
                      + f"{mean[46]['relevance']:>10.3f}")
                for n in NS:
                    rows.append(dict(dim=d, sigma=sigma, n=n, surrogate=name,
                                     **mean[n]))
            print(f"{'':>20} coverage should be 0.950 · relevance chance = "
                  f"{chance:.3f}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1))
    print(f"\nrows written to {OUT}")
    print("\nREAD THIS AS: which code changes make the model predict better. It "
          "does NOT\nsay whether better predictions buy better regret — Q26 "
          "found cells where those\ncome apart in both directions.")


if __name__ == "__main__":
    main()
