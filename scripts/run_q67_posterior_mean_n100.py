"""Q67 — power extension of the posterior-mean contrast at sigma = 0.10. CONFIRMATORY.

    python scripts/run_q67_posterior_mean_n100.py --workers 6

WHAT THIS CONFIRMS OR KILLS
---------------------------
Q66 (exploratory, n=25) found the only BO win available from a zero-well readout change:

    sigma = 0.10, DoE - BO[posterior_mean] = +0.0181 [+0.0073, +0.0292], Wilcoxon p = 0.0074

BO both searched better (0.0415 vs 0.0544) and identified better (0.0296 vs 0.0361). But
**the effect is smaller than the design's own resolution**: at n = 25 the MDE is ~0.027
against an effect of 0.0181. A directional result inside its own noise floor is a lead,
not a finding. This run supplies the power.

At sigma = 0.25 the same rule does nothing (0.1553 vs 0.1552 for the noisy argmax), which
is consistent with the GP being miscalibrated at high noise (worst latent coverage 0.764):
pooling cannot rescue a surrogate that is wrong about its own uncertainty. A rule that won
everywhere would be the suspicious outcome; this one wins where the mechanism says it can.

THE ENSEMBLE, AND WHY THE REGISTERED ANALYSIS SURVIVES
-----------------------------------------------------
`generate_ensemble` accepts landscapes sequentially from `seed0`, so drawing 100 with the
committed SamplerConfig reproduces the committed 25 as an exact prefix and appends 75.
**Verified before this run: the first 25 instance_ids and seeds are identical.** The
registered n = 25 analysis is therefore an exact subset, not a replacement, and both are
reported. The extended ensemble is written to a separate root so `data/oracles/` is not
mutated -- adding sidecars there would silently change `load_ensemble` for every other
script and every test in the repo.

**Status.** This is a declared post-hoc power extension, not the prespecified analysis.
It is reported alongside n = 25, never instead of it.

THE GATE
--------
For the 25 landscapes that overlap, the DoE arm must reproduce Q57's stored `doe_rule_a`
**bit-exactly**. That gate ties the extended ensemble back to committed results and would
catch a prefix that had silently drifted. The DoE arm replays at delta 0.0 because it
never touches the acquisition optimizer.

BO is not gated against stored values and cannot be: stored BO results are not
reproducible from code and seed, because BoTorch's acquisition retry depended on
per-process warning state. Replaying Q57 at its own commit in a byte-identical
environment gave some rows bit-exact and others off by 1.2e-01. The BO baseline here is
this run's own measured-value argmax arm.
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

from scipy.stats import wilcoxon                                      # noqa: E402

from boec.campaign import Campaign, CampaignConfig                    # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.selection import posterior_mean_at_visited                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402
from boec.tost import tost_paired, wilcoxon_mde                       # noqa: E402

BUDGET, Q, ACQ = 48, 4, "qlognei"
DIM, SIGMA = 6, 0.10
N_SEEDS = 2
SESOI = 0.02
Q57 = ROOT / "results" / "q57-search-vs-id.json"
OUT = ROOT / "results" / "q67-posterior-mean-n100.json"
ENS_ROOT = Path(os.environ.get("BOEC_ENSEMBLE_ROOT", ROOT / "data" / "oracles"))


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def one(job: tuple[int, int]) -> dict:
    idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM, root=ENS_ROOT)[idx]
    opt = float(inst.optimum_value)
    bounds = _bounds(DIM)

    o = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    camp = Campaign(o, bounds, CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=seed,
                                              acq=AcqConfig(kind=ACQ))).run()
    X, Y = camp.train_X, camp.train_Y
    t = o.truth(X).double().reshape(-1)
    model = camp.fit()

    def mean_fn(Z):
        with torch.no_grad():
            return model.posterior(Z).mean

    i_pm = posterior_mean_at_visited(mean_fn, X.double())

    od = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    r = run_doe_arm(od, bounds, truth=od.truth, budget=BUDGET, seed=seed)
    dt = od.truth(r.X_visited)

    return dict(
        instance=inst.instance_id, instance_index=idx, seed=seed, dim=DIM, sigma=SIGMA,
        bo_measured=opt - float(reported_best_curve(o.truth(X), Y)[-1]),
        bo_posterior_mean=opt - float(t[i_pm]),
        bo_search=opt - float(t.max()),
        doe_measured=opt - float(reported_best_curve(dt, r.Y_visited)[-1]),
        doe_search=opt - float(dt.double().reshape(-1).max()),
        secs=round(time.time() - t0, 1))


def _gate(rows: list[dict]) -> dict:
    stored = {(r["instance"], r["seed"]): r["doe_rule_a"]
              for r in json.loads(Q57.read_text())["rows"]
              if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-9}
    worst, checked = 0.0, 0
    for r in rows:
        k = (r["instance"], r["seed"])
        if k in stored:
            worst = max(worst, abs(r["doe_measured"] - stored[k]))
            checked += 1
    if checked < 20:
        raise SystemExit(f"gate overlapped only {checked} rows; prefix is not intact")
    if worst != 0.0:
        raise SystemExit(f"DoE arm does not reproduce Q57: worst {worst:.3e}; stop.")
    return dict(overlap_rows=checked, doe_worst_abs_delta=worst,
                bo_note="BO not gated: stored BO is not reproducible from code+seed.")


def _by_instance(rows: list[dict], key: str, keep: set[str] | None = None) -> np.ndarray:
    by: dict[str, list[float]] = {}
    for r in rows:
        if keep is not None and r["instance"] not in keep:
            continue
        by.setdefault(r["instance"], []).append(r[key])
    return np.array([np.mean(v) for _, v in sorted(by.items())])


def analyse(rows: list[dict], keep: set[str] | None, label: str) -> dict:
    doe = _by_instance(rows, "doe_measured", keep)
    out = dict(label=label, n=len(doe))
    for rule in ("bo_measured", "bo_posterior_mean"):
        bo = _by_instance(rows, rule, keep)
        diff = doe - bo
        m, lo, hi = instance_bootstrap(diff)
        t = tost_paired(diff, sesoi=SESOI)
        out[rule] = dict(
            doe_mean=float(doe.mean()), bo_mean=float(bo.mean()),
            contrast=float(m), lo=float(lo), hi=float(hi),
            wilcoxon_p=float(wilcoxon(diff).pvalue),
            mde=float(wilcoxon_mde(len(diff))) if callable(wilcoxon_mde) else None,
            tost_verdict=t.get("verdict"), tost_equivalent=bool(t.get("equivalent")))
    out["bo_search"] = float(_by_instance(rows, "bo_search", keep).mean())
    out["doe_search"] = float(_by_instance(rows, "doe_search", keep).mean())
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--n-instances", type=int, default=100)
    a = p.parse_args()

    n_avail = len(load_ensemble(dim=DIM, root=ENS_ROOT))
    n = min(a.n_instances, n_avail)
    jobs = [(i, s) for i in range(n) for s in range(N_SEEDS)]
    print(f"Q67 CONFIRMATORY — d={DIM} sigma={SIGMA}, n={n} landscapes x {N_SEEDS} seeds")
    print(f"  ensemble root: {ENS_ROOT}\n")

    rows: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for k, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if k % 25 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

    gate = _gate(rows)
    print(f"\nDoE gate OK: {gate['overlap_rows']} overlapping rows bit-exact vs Q57\n")

    registered = {r["instance"] for r in rows if r["instance_index"] < 25}
    results = [analyse(rows, registered, "n=25 registered subset"),
               analyse(rows, None, f"n={n} power extension")]

    OUT.write_text(json.dumps(dict(
        ticket="Q67", status="CONFIRMATORY power extension; reported ALONGSIDE n=25",
        config=dict(dim=DIM, sigma=SIGMA, budget=BUDGET, q=Q, acq=ACQ, sesoi=SESOI,
                    ensemble_root=str(ENS_ROOT)),
        provenance=dict(
            git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
            argv=sys.argv, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        gate=gate, results=results, rows=rows), indent=1) + "\n")
    print(f"wrote {OUT}\n")

    for res in results:
        print(f"--- {res['label']}  (n={res['n']})")
        print(f"    search: DoE {res['doe_search']:.4f}   BO {res['bo_search']:.4f}")
        for rule in ("bo_measured", "bo_posterior_mean"):
            d = res[rule]
            v = "BO BETTER" if d["lo"] > 0 else ("DoE better" if d["hi"] < 0 else "not separated")
            print(f"    DoE {d['doe_mean']:.4f}  BO[{rule[3:]:<15}] {d['bo_mean']:.4f}  "
                  f"contrast {d['contrast']:+.4f} [{d['lo']:+.4f},{d['hi']:+.4f}]  "
                  f"p={d['wilcoxon_p']:.4f}  {v}  TOST:{d['tost_verdict']}")
        print()


if __name__ == "__main__":
    main()
