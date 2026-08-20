"""Q69 / B4 — can the GP's uncertainty be repaired? Sweeps build_gp against COVERAGE.

    BOEC_ENSEMBLE_ROOT=<ext> python scripts/run_q69_calibration.py --workers 6

THE PROBLEM, AND WHY IT IS NOT COSMETIC
---------------------------------------
Nominal 95% posterior intervals for the LATENT response cover as little as **76.4%**.
Two of the project's seven terminal rules -- posterior-mean selection and the GP optimum --
read that posterior, so both are currently reported "conditional on a miscalibrated
surrogate", which is honest and nearly useless. The acquisition function reads it too: EI
and its variants trade exploration against exploitation using exactly the uncertainty that
is wrong, so miscalibration is upstream of where BO samples, not only of how it is scored.

This is repair, not tuning. `START-HERE-PERSON-A.md` Q5 forbids upgrading one arm while the
baseline keeps defaults; fixing a component that is measurably wrong is not the same as
tuning a component that works. No arm's *policy* changes here -- only whether its stated
uncertainty is true. Nothing in this file feeds a headline contrast; it feeds the decision
about whether the two GP-dependent rules can stop carrying a caveat.

WHAT IS SWEPT
-------------
`build_gp` already exposes every knob used below; none has previously been swept against
coverage as the objective.

    baseline            product kernel, dim_scaled lengthscale prior, 1 fit restart
    gamma_prior         lengthscale_prior="gamma"
    additive            kernel_structure="additive"
    additive_inter      kernel_structure="additive+interaction"
    warped              input_warping=True   (Hill factors are biphasic; a warp may help)
    restarts4           fit_restarts=4       (is this just a bad-MLE problem?)
    warped_restarts4    the two most plausible fixes together

MEASURED ON HELD-OUT POINTS, AGAINST THE LATENT TRUTH
-----------------------------------------------------
Coverage is evaluated at each campaign's own `holdout_X` -- 64 Sobol points drawn at
`seed + 10_000`, fixed before the campaign runs and never trained on -- scored against
`oracle.truth`, the NOISELESS value. Coverage against noisy observations is a different and
easier quantity; the number the paper quotes, and the one the GP-dependent rules need, is
latent coverage.

**Coverage is reported next to sharpness, always.** Coverage alone is trivially perfect for
a model that predicts +/- infinity, so a config that "fixes" coverage by inflating intervals
has not fixed anything. A repair means coverage near 0.95 WITHOUT a large sharpness
increase. PIT is also recorded: it checks the shape of the predictive distribution rather
than one interval, and a config can hit 95% coverage with a badly wrong PIT.

REGISTERED PREDICTION, BEFORE THE RUN
-------------------------------------
Under-coverage of the latent at high noise is most likely the model absorbing signal into
its noise term -- fitting sigma too large and the signal variance too small, which
paradoxically makes LATENT intervals too NARROW because the latent posterior excludes the
noise it has over-attributed. If that is the mechanism:
  * `restarts4` should help only marginally -- it is an optimiser fix for what is a
    model-specification problem.
  * `warped` should help if the biphasic shape is being fitted as noise.
  * `additive` should help if cross-factor structure is what the product kernel is missing.
Expected: some config improves coverage materially; none reaches 0.95 without paying in
sharpness. Recorded so it can be scored rather than reconstructed.
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
from boec.diagnostics import coverage, sharpness                      # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.surrogate import build_gp                                   # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402

BUDGET, Q, ACQ = 48, 4, "qlognei"
DIM = 6
N_SEEDS = 2
OUT = ROOT / "results" / "q69-calibration.json"
ENS_ROOT = Path(os.environ.get("BOEC_ENSEMBLE_ROOT", ROOT / "data" / "oracles"))

CONFIGS = {
    "baseline":         {},
    "gamma_prior":      {"lengthscale_prior": "gamma"},
    "additive":         {"kernel_structure": "additive"},
    "additive_inter":   {"kernel_structure": "additive+interaction"},
    "warped":           {"input_warping": True},
    "restarts4":        {"fit_restarts": 4},
    "warped_restarts4": {"input_warping": True, "fit_restarts": 4},
}


def _bounds(d):
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _pit(y, mean, sd):
    """Probability integral transform values; uniform if the predictive is right."""
    from torch.distributions import Normal
    return Normal(mean.reshape(-1), sd.reshape(-1)).cdf(y.reshape(-1))


def one(job):
    idx, seed, sigma = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM, root=ENS_ROOT)[idx]
    bounds = _bounds(DIM)
    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    camp = Campaign(o, bounds, CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=seed,
                                              acq=AcqConfig(kind=ACQ))).run()
    Xh = camp.holdout_X.double()
    y_latent = o.truth(Xh).double().reshape(-1, 1)

    out = dict(instance=inst.instance_id, instance_index=idx, seed=seed, sigma=sigma)
    for name, kw in CONFIGS.items():
        try:
            model = build_gp(camp.train_X, camp.train_Y, camp.train_Yvar, bounds, **kw)
            with torch.no_grad():
                post = model.posterior(Xh)
                mean = post.mean.double().reshape(-1, 1)
                sd = post.variance.clamp_min(1e-12).sqrt().double().reshape(-1, 1)
            cov = float(coverage(y_latent, mean, sd, alpha=0.05))
            shp = float(sharpness(sd))
            pit = _pit(y_latent, mean, sd)
            # KS distance from uniform: shape check, not just one interval.
            u = torch.sort(pit).values.numpy()
            n = len(u)
            ks = float(np.max(np.abs(u - (np.arange(1, n + 1) - 0.5) / n)))
            out[name] = dict(coverage=cov, sharpness=shp, pit_ks=ks, failed=None)
        except Exception as exc:                       # noqa: BLE001 - recorded as a rate
            out[name] = dict(coverage=None, sharpness=None, pit_ks=None,
                             failed=f"{type(exc).__name__}: {exc}")
    out["secs"] = round(time.time() - t0, 1)
    return out


def summarize(rows):
    res = []
    for sigma in sorted({r["sigma"] for r in rows}):
        sub = [r for r in rows if r["sigma"] == sigma]
        for name in CONFIGS:
            ok = [r[name] for r in sub if r[name]["coverage"] is not None]
            if not ok:
                res.append(dict(sigma=sigma, config=name, n=0,
                                fail_rate=1.0, coverage=None))
                continue
            res.append(dict(
                sigma=sigma, config=name, n=len(ok),
                fail_rate=round(1 - len(ok) / len(sub), 3),
                coverage=float(np.mean([x["coverage"] for x in ok])),
                coverage_min=float(np.min([x["coverage"] for x in ok])),
                sharpness=float(np.mean([x["sharpness"] for x in ok])),
                pit_ks=float(np.mean([x["pit_ks"] for x in ok]))))
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--n-instances", type=int, default=25)
    p.add_argument("--sigmas", default="0.25,0.10")
    a = p.parse_args()
    sigmas = [float(x) for x in a.sigmas.split(",")]
    n = min(a.n_instances, len(load_ensemble(dim=DIM, root=ENS_ROOT)))
    jobs = [(i, s, sg) for sg in sigmas for i in range(n) for s in range(N_SEEDS)]
    print(f"Q69 calibration sweep — {len(jobs)} campaigns x {len(CONFIGS)} GP configs")
    print(f"  latent coverage on 64 held-out Sobol points, nominal 0.95\n")
    rows, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for k, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if k % 20 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    summary = summarize(rows)
    OUT.write_text(json.dumps(dict(
        ticket="Q69", status="Diagnostic sweep; repairs a defect, changes no arm's policy.",
        note="Latent coverage at held-out Sobol points vs oracle.truth. Nominal 0.95. "
             "Coverage is meaningless without sharpness; both reported, plus PIT KS.",
        configs=CONFIGS,
        provenance=dict(git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                        capture_output=True, text=True).stdout.strip(),
                        argv=sys.argv, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        summary=summary, rows=rows), indent=1) + "\n")
    print(f"wrote {OUT}\n")
    for sigma in sorted({s["sigma"] for s in summary}):
        print(f"--- sigma = {sigma}   (nominal coverage 0.95)")
        print(f"    {'config':<18}{'coverage':>9}{'min':>8}{'sharpness':>11}{'PIT KS':>8}{'fail':>7}")
        for s in [x for x in summary if x["sigma"] == sigma]:
            if s["coverage"] is None:
                print(f"    {s['config']:<18}{'ALL FAILED':>9}"); continue
            print(f"    {s['config']:<18}{s['coverage']:>9.3f}{s['coverage_min']:>8.3f}"
                  f"{s['sharpness']:>11.4f}{s['pit_ks']:>8.3f}{s['fail_rate']:>7.0%}")
        print()


if __name__ == "__main__":
    main()
