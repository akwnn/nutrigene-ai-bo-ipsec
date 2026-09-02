"""E3 — calibration. When the model says it is confident, should you believe it?

OWNERSHIP: Person A. Reproduce with `python scripts/run_e3.py`.

Not "is the guess good" but "is the *uncertainty* honest". A model that is usually right
and wildly overconfident when wrong is more dangerous in a lab than a vaguer honest one,
because the confident-and-wrong case is the one that becomes an experiment.

**Prospective, at two point sets, which is the design that makes this credible.** Each
round the campaign records what it believed BEFORE measuring — B's `RoundLog` captures
exactly this and it cannot be reconstructed afterwards. We score:

* **at BO-proposed points** — decision-relevant, but this is coverage *under a selection
  rule*, since acquisition deliberately seeks high-mean and high-variance regions;
* **at a fixed held-out Sobol set** — domain-wide, no selection effect.

**The gap between them is itself the finding** and is reported, not averaged away.

**Latent versus predictive.** `predictive(model, X)` with no noise gives the smooth
underlying response; what a lab measures also carries observation noise. Both are
reported and labelled, because they answer different questions and conflating them is a
silent error. The predictive variance is the latent variance plus the plug-in noise at
that point, in raw units — B verified the additivity in PF3.

**Never `posterior(..., observation_noise=True)`.** It substitutes the mean of the
training noise flat across every query point, which is exactly where E3's headline lives.

Error bars are mandatory: coverage at nominal 0.95 with n=48 has a standard error near
3.1%, so 95% and 89% are indistinguishable in one run. Bootstrapped over **instances**.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from boec.campaign import Campaign, CampaignConfig
from boec.diagnostics import coverage, crps_gaussian, instance_bootstrap, pit_values, sharpness
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

DIMS = (6, 8)
SIGMAS = (0.25, 0.10)
N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
ALPHA = 0.05


def unit_bounds(d):
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def score(y_true, mean, var_latent, sigma_rel, sigma_add):
    """Latent and predictive scores at one set of points.

    Predictive variance = latent + plug-in noise, in raw outcome units. The plug-in
    uses the model's own mean as yhat, because at an unrun point there is no
    observation -- and that is a stated modelling assumption, not a measurement.
    """
    plug_in = np.maximum(mean**2 * sigma_rel**2 + sigma_add**2, sigma_add**2)
    out = {}
    for tag, var in (("latent", var_latent), ("predictive", var_latent + plug_in)):
        sd = var.clamp_min(1e-300).sqrt()
        out[f"cov_{tag}"] = float(coverage(y_true, mean, sd, alpha=ALPHA))
        out[f"crps_{tag}"] = float(crps_gaussian(y_true, mean, sd).mean())
        out[f"sharp_{tag}"] = float(sharpness(sd))
        out[f"pit_{tag}"] = pit_values(y_true, mean, sd).numpy().ravel()
    return out


def run_cell(inst, dim, sigma, seed) -> list[dict]:
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    c = Campaign(orc, unit_bounds(dim), CampaignConfig(d=dim, budget=BUDGET, q=4,
                                                       seed=seed))
    c.run()
    rows = []
    for log in c.logs:
        if log.mean_proposed is None:          # the opening design: no model existed
            continue
        for where, X, mean, var in (
            ("proposed", log.X_proposed, log.mean_proposed, log.var_proposed),
            ("holdout", c.holdout_X, log.mean_holdout, log.var_holdout),
        ):
            f = orc.truth(X)
            # What a lab would MEASURE there -- a fresh noisy draw, not the truth.
            rng = np.random.default_rng(hash((inst.instance_id, seed, log.round_index,
                                              where)) % (2**32))
            eps = rng.normal(0, sigma, f.shape)
            eta = rng.normal(0, 0.01, f.shape)
            y_meas = f * (1 + torch.from_numpy(eps)) + torch.from_numpy(eta)
            s_lat = score(f, mean, var, sigma, 0.01)          # latent vs the TRUTH
            s_pre = score(y_meas, mean, var, sigma, 0.01)     # predictive vs a MEASUREMENT
            rows.append(dict(
                instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                where=where, round=log.round_index, n_train=log.n_train_before,
                cov_latent=s_lat["cov_latent"], crps_latent=s_lat["crps_latent"],
                sharp_latent=s_lat["sharp_latent"],
                cov_predictive=s_pre["cov_predictive"],
                crps_predictive=s_pre["crps_predictive"],
                sharp_predictive=s_pre["sharp_predictive"],
            ))
    return rows


def main() -> None:
    rows = []
    for dim in DIMS:
        for sigma in SIGMAS:
            for inst in load_ensemble(dim=dim)[:N_INSTANCES]:
                for seed in range(N_SEEDS):
                    rows.extend(run_cell(inst, dim, sigma, seed))
            print(f"  d={dim} sigma={sigma} done ({len(rows)} rows)", flush=True)

    Path("results").mkdir(exist_ok=True)
    Path("results/e3-grid.json").write_text(json.dumps(rows, indent=1))
    report(rows)


def report(rows) -> None:
    for dim in DIMS:
        for sigma in SIGMAS:
            sub = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma]
            if not sub:
                continue
            insts = sorted({r["instance"] for r in sub})
            print(f"\n{'=' * 86}\nE3 · d={dim} · sigma_rel={sigma} · "
                  f"{len(insts)} instances\n{'=' * 86}")
            print(f"{'point set':>10} {'kind':>12} {'coverage (nominal 0.95)':>32} "
                  f"{'sharpness':>11} {'CRPS':>9}")
            store = {}
            for where in ("proposed", "holdout"):
                for kind in ("latent", "predictive"):
                    per_inst = np.array([
                        np.mean([r[f"cov_{kind}"] for r in sub
                                 if r["instance"] == i and r["where"] == where])
                        for i in insts])
                    m, lo, hi = instance_bootstrap(per_inst, n_boot=2000)
                    store[(where, kind)] = per_inst
                    sh = np.mean([r[f"sharp_{kind}"] for r in sub if r["where"] == where])
                    cr = np.mean([r[f"crps_{kind}"] for r in sub if r["where"] == where])
                    flag = "" if lo <= 0.95 <= hi else "   <-- MISCALIBRATED"
                    print(f"{where:>10} {kind:>12} {m:>12.4f}  [{lo:.4f}, {hi:.4f}]"
                          f"{flag:>0} {sh:>11.4f} {cr:>9.4f}")

            for kind in ("latent", "predictive"):
                gap = store[("proposed", kind)] - store[("holdout", kind)]
                m, lo, hi = instance_bootstrap(gap, n_boot=2000)
                print(f"\n  SELECTION-EFFECT GAP ({kind}), proposed minus holdout: "
                      f"{m:+.4f} [{lo:+.4f}, {hi:+.4f}]")
            print("  Negative means coverage is WORSE where the optimizer chose to look "
                  "-- the\n  decision-relevant points. That gap is a finding, not noise "
                  "to average away.")


if __name__ == "__main__":
    main()
