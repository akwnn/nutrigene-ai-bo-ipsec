"""SPADE's certificate on the REAL iPSC-EC coating data, against real baselines.

**PROVISIONAL.** `data/lab/derived/candidate_campaign_coating_flow.csv` carries
`status = awaiting_human_signoff`: the CD31 gate has not been signed by a person, and
`data/lab/overlay/GATE.md` is explicit that `bo_primary_conditions.csv`'s `y` stays empty
until it is. Nothing here may be reported as a wet-lab result. It is a demonstration that
the method RUNS on real cells at real noise, and that is all it is.

Noise is `y_spread_pp` -- the measured spread of the positivity call across gate
thresholds (p95 vs p99.9). That is a real, per-tube uncertainty from the instrument
files, not an assumed sigma. It is the honest input and it is large: 10.8-14.1 pp on
values averaging 38.7%.

Design space: coating (fibronectin=0, vitronectin=1) x log10 dose, both scaled to [0,1].
Question a manufacturing lab actually asks: *which coating conditions reliably reach
CD31+ >= tau?*
"""
from __future__ import annotations

import csv, sys, warnings
from pathlib import Path

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SRC = ROOT / "data/lab/derived/candidate_campaign_coating_flow.csv"
#: Manufacturing spec sweep. 40% sits at the median of the 12 measured tubes.
TAUS = (25.0, 28.0, 30.0, 32.0, 35.0)
#: Calibration levers. c=1.0 is the identity control.
CS = (1.0, 1.5, 2.0, 3.0)
ALPHAS = (0.5, 0.8, 0.95)
N_DRAWS = 4000


def load():
    X, Y, S = [], [], []
    for r in csv.DictReader(open(SRC)):
        assert r["status"] == "awaiting_human_signoff", r["status"]
        dose = float(r["dose_ug_mL"])
        # log10 dose over the measured box 0.5-20 ug/mL, scaled to [0,1].
        d = (torch.log10(torch.tensor(dose)) - torch.log10(torch.tensor(0.5))) / (
            torch.log10(torch.tensor(20.0)) - torch.log10(torch.tensor(0.5)))
        X.append([float(r["coating_coded"]), float(d)])
        Y.append(float(r["y_candidate"]))
        S.append(float(r["y_spread_pp"]))
    return (torch.tensor(X, dtype=torch.double),
            torch.tensor(Y, dtype=torch.double).unsqueeze(-1),
            torch.tensor(S, dtype=torch.double).unsqueeze(-1) ** 2)


def main():
    from boec.surrogate import build_gp
    from boec.topk import certified_topk
    from boec.vorobev import conservative_estimate, excursion_probability

    X, Y, Yvar = load()
    print(f"REAL DATA: {X.shape[0]} iPSC-EC coating conditions, "
          f"CD31% mean {Y.mean():.1f}, measured noise sd "
          f"{Yvar.sqrt().mean():.1f} pp  (CV {100*Yvar.sqrt().mean()/Y.mean():.0f}%)")
    print("STATUS: awaiting_human_signoff -- PROVISIONAL, not a wet-lab result\n")

    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    m = build_gp(X, Y, Yvar, bounds)

    # Dense candidate grid over the real design box.
    g = torch.linspace(0, 1, 101, dtype=torch.double)
    cand = torch.cartesian_prod(torch.tensor([0.0, 1.0], dtype=torch.double), g)

    from boec.meanmarg import mean_marginalised_covariance
    with torch.no_grad():
        post = m.posterior(cand)
        mean = post.mean.reshape(-1, 1)
        raw = post.mvn.covariance_matrix.double()
        cov = mean_marginalised_covariance(m, cand)
        print(f"posterior sd  raw {raw.diagonal().sqrt().mean():.3f}"
              f"  ->  mean-marginalised {cov.diagonal().sqrt().mean():.3f}\n")
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        gen = torch.Generator().manual_seed(0)
        z = torch.randn(cov.shape[0], N_DRAWS, generator=gen, dtype=torch.double)

    for tau in TAUS:
        print(f"===== manufacturing spec: CD31+ >= {tau:.0f}% =====")
        print(f"{'c':>5}{'alpha':>7}{'region vol':>12}{'topk n':>9}{'best dose':>28}")
        for c in CS:
            with torch.no_grad():
                draws = (mean + c * L @ z).T
            for a in ALPHAS:
                ce = conservative_estimate(draws, tau, a)
                vol = float(ce.double().mean())
                idx = certified_topk(draws, tau, a)
                if idx:
                    # report the certified condition with the highest posterior mean
                    sub = cand[idx]
                    best = int(torch.argmax(mean.reshape(-1)[idx]))
                    coat = "FN" if sub[best, 0] < 0.5 else "VTN"
                    dose = 0.5 * (20.0 / 0.5) ** float(sub[best, 1])
                    desc = f"{coat} {dose:.1f} ug/mL ({len(idx)} certified)"
                else:
                    desc = "-- nothing certified --"
                print(f"{c:>5}{a:>7}{vol:>12.4f}{len(idx):>9}{desc:>28}")
        print()


if __name__ == "__main__":
    main()
