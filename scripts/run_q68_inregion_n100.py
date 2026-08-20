"""Q68 — the PRIMARY in-region contrast at n=100. Closes G2's headline purpose.

    BOEC_ENSEMBLE_ROOT=<extended> python scripts/run_q68_inregion_n100.py --workers 6

THE GAP THIS CLOSES
-------------------
Table 3's primary cell -- d=6, sigma=0.25, in-region model recommendation -- reads
**-0.0063 [-0.0233, +0.0107], inconclusive**, with MDE ~0.027 against a SESOI of 0.02.
That is the fair-readout comparison, the answer to "what would a careful RSM practitioner
actually ship", and as written the paper cannot say anything about it. It is underpowered,
not null: the design cannot resolve the effect it was built to test.

n = 100 puts the MDE near 0.0135, inside the SESOI, so the cell can return a verdict:
a real difference, or a declared equivalence. Given the point estimate is -0.0063, the
likely outcome is equivalence, which is a considerably stronger claim than "inconclusive"
and is the sentence that makes the terminal-rule thesis land -- the whole gap lives in the
readout, not in the method.

WHAT Q64 SETTLED FIRST, AND WHY IT MATTERED
------------------------------------------
Until Q64 ran, Table 3 compared a CONSTRAINED quadratic against an UNCONSTRAINED GP:
`paper_figures.py` reused the stored box peak for the GP's in-region bar on the strength
of a manuscript assertion, and no field in q34 or q35 recorded whether that assertion
held. Q64 checked it -- the GP peak lies inside the sampled region in **100/100**
campaigns at the primary cell, box and region regret differing by 1.5e-06. The assertion
was correct. This run computes the region-constrained GP peak explicitly anyway, via
`sampled_region_bounds`, so the number is measured rather than inherited.

THE ENSEMBLE
------------
`generate_ensemble` accepts sequentially from seed0, so 100 landscapes reproduce the
committed 25 as an exact prefix (verified: instance_ids and seeds identical). n=25 is
reported ALONGSIDE n=100, never replaced -- this is a declared post-hoc power extension,
not the prespecified analysis. The extended ensemble lives under a separate root; writing
sidecars into data/oracles/ would silently change `load_ensemble` for every script and
test in the repo.

GATES
-----
1. DoE measured-value argmax must reproduce Q57's stored `doe_rule_a` BIT-EXACTLY on the
   25 overlapping landscapes. Ties the extended ensemble back to committed results.
2. The stage-2 refit must reproduce the arm's own predicted optimum to 1e-6 (q35's
   REFIT_TOL). If the refit is not the arm's model, everything scored off it describes a
   different surface and the comparison is void.

BO is not gated against stored values and cannot be: stored BO results are not reproducible
from code and seed (acquisition retry depended on per-process warning state; replaying Q57
at its own commit gave rows off by up to 1.2e-01). Each run carries its own BO baseline.
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
from boec.metrics import (constrained_argmax, point_in_region,        # noqa: E402
                          sampled_region_bounds)
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import load_ensemble                                # noqa: E402
from boec.rsm import fit_second_order                                 # noqa: E402
from boec.surrogate import build_gp                                   # noqa: E402
from boec.torch_oracle import BiphasicOracle                          # noqa: E402
from boec.tost import tost_paired                                     # noqa: E402

BUDGET, Q = 48, 4
DIM, SIGMA = 6, 0.25
N_SEEDS, SESOI = 2, 0.02
N_RESTARTS, RAW_SAMPLES, REFIT_TOL = 20, 4096, 1e-6
Q57 = ROOT / "results" / "q57-search-vs-id.json"
OUT = ROOT / "results" / os.environ.get("BOEC_OUT_NAME", "q68-inregion-n100.json")
ENS_ROOT = Path(os.environ.get("BOEC_ENSEMBLE_ROOT", ROOT / "data" / "oracles"))


def _ensemble(dim: int):
    """Load from ENS_ROOT, auto-detecting the version-stamped subdirectory.

    An alternate ensemble (different SamplerConfig) hashes to a different version dir, so
    hardcoding the default version silently fails on it rather than loading the wrong one.
    """
    vers = [q for q in ENS_ROOT.iterdir() if (q / "sidecars").is_dir()]
    if len(vers) != 1:
        raise SystemExit(f"expected exactly one oracle version under {ENS_ROOT}, got {vers}")
    return load_ensemble(dim=dim, root=ENS_ROOT, version=vers[0].name)


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _gp_peaks(X, Y, Yvar, bounds, seed):
    """Unconstrained (whole box) and region-constrained GP peaks, plus containment."""
    model = build_gp(X, Y, Yvar, bounds)

    def predict(Z):
        with torch.no_grad():
            return model.posterior(Z).mean

    x_box, _, _ = constrained_argmax(predict, bounds, n_restarts=N_RESTARTS,
                                     raw_samples=RAW_SAMPLES, seed=seed)
    region = sampled_region_bounds(X)
    x_reg, _, _ = constrained_argmax(predict, region, n_restarts=N_RESTARTS,
                                     raw_samples=RAW_SAMPLES, seed=seed)
    return (x_box.reshape(1, -1), x_reg.reshape(1, -1),
            bool(point_in_region(x_box, region)))


def one(job: tuple[int, int]) -> dict:
    idx, seed = job
    t0 = time.time()
    inst = _ensemble(DIM)[idx]
    opt = float(inst.optimum_value)
    bounds = _bounds(DIM)
    row = dict(instance=inst.instance_id, instance_index=idx, seed=seed,
               dim=DIM, sigma=SIGMA)

    # ---- classical arm: measured argmax, and the in-region (ridge-style) readout ----
    od = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    r = run_doe_arm(od, bounds, truth=od.truth, budget=BUDGET, seed=seed)
    kept = list(r.kept_factors)
    s2 = slice(r.n_stage1, r.n_stage1 + r.n_stage2)
    fit = fit_second_order(r.X_visited[s2][:, kept], r.Y_visited[s2])

    def lift(x_kept):
        full = torch.tensor([r.dropped_held_at.get(i, 0.0) for i in range(DIM)],
                            dtype=torch.double)
        full[kept] = x_kept.double().reshape(-1)
        return full.unsqueeze(0)

    x_un, y_un, _ = constrained_argmax(fit.predict, r.search_bounds,
                                       n_restarts=N_RESTARTS,
                                       raw_samples=RAW_SAMPLES, seed=seed)
    drift = float(np.abs(y_un - r.predicted_y))
    if drift > REFIT_TOL:
        raise AssertionError(
            f"stage-2 refit does not reproduce the arm's predicted optimum: "
            f"|delta| {drift:.3e} at {inst.instance_id} seed={seed}")
    x_con, _, _ = constrained_argmax(fit.predict, r.stage2_bounds,
                                     n_restarts=N_RESTARTS,
                                     raw_samples=RAW_SAMPLES, seed=seed)
    row |= dict(
        doe_measured=opt - float(reported_best_curve(od.truth(r.X_visited),
                                                     r.Y_visited)[-1]),
        doe_unconstrained=opt - float(od.truth(lift(x_un))),
        doe_inregion=opt - float(od.truth(lift(x_con))),
        refit_drift=drift, n_kept=len(kept))

    # ---- BO arms ----
    for tag, kind in (("qlogei", "qlogei"), ("qlognei", "qlognei")):
        o = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
        camp = Campaign(o, bounds, CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=seed,
                                                  acq=AcqConfig(kind=kind))).run()
        x_box, x_reg, inside = _gp_peaks(camp.train_X, camp.train_Y,
                                         camp.train_Yvar, bounds, seed)
        row |= {
            f"{tag}_measured": opt - float(reported_best_curve(
                o.truth(camp.train_X), camp.train_Y)[-1]),
            f"{tag}_gp_box": opt - float(o.truth(x_box)),
            f"{tag}_gp_inregion": opt - float(o.truth(x_reg)),
            f"{tag}_peak_inside_region": inside,
        }
    row["secs"] = round(time.time() - t0, 1)
    return row


def _gate(rows):
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
        if os.environ.get("BOEC_ALT_ORACLE"):
            return dict(overlap_rows=checked, doe_worst_abs_delta=None,
                        max_refit_drift=max(r["refit_drift"] for r in rows),
                        note="alternate oracle family: no committed prefix to gate against; "
                             "the refit-fidelity gate still applies")
        raise SystemExit(f"gate overlapped only {checked} rows; prefix not intact")
    if worst != 0.0:
        raise SystemExit(f"DoE arm does not reproduce Q57: worst {worst:.3e}")
    return dict(overlap_rows=checked, doe_worst_abs_delta=worst,
                max_refit_drift=max(r["refit_drift"] for r in rows),
                refit_tol=REFIT_TOL)


def _per(rows, key, keep):
    by = {}
    for r in rows:
        if keep is None or r["instance"] in keep:
            by.setdefault(r["instance"], []).append(r[key])
    return np.array([np.mean(v) for _, v in sorted(by.items())])


def analyse(rows, keep, label):
    out = dict(label=label, n=len(_per(rows, "doe_measured", keep)))
    pairs = [("in-region: DoE quad vs qLogEI GP", "doe_inregion", "qlogei_gp_inregion"),
             ("in-region: DoE quad vs qLogNEI GP", "doe_inregion", "qlognei_gp_inregion"),
             ("measured argmax: DoE vs qLogEI", "doe_measured", "qlogei_measured"),
             ("unconstrained: DoE quad vs qLogEI GP", "doe_unconstrained", "qlogei_gp_box")]
    out["contrasts"] = []
    for name, a, b in pairs:
        da, db = _per(rows, a, keep), _per(rows, b, keep)
        diff = da - db
        m, lo, hi = instance_bootstrap(diff)
        t = tost_paired(diff, sesoi=SESOI)
        out["contrasts"].append(dict(
            name=name, doe_mean=float(da.mean()), bo_mean=float(db.mean()),
            contrast=float(m), lo=float(lo), hi=float(hi),
            wilcoxon_p=float(wilcoxon(diff).pvalue),
            tost_verdict=t.get("verdict"), tost_equivalent=bool(t.get("equivalent"))))
    ins = [r for r in rows if keep is None or r["instance"] in keep]
    out["gp_peak_inside_region_rate"] = float(np.mean(
        [r["qlogei_peak_inside_region"] for r in ins]))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--n-instances", type=int, default=100)
    a = p.parse_args()
    n = min(a.n_instances, len(_ensemble(DIM)))
    jobs = [(i, s) for i in range(n) for s in range(N_SEEDS)]
    print(f"Q68 — primary cell d={DIM} sigma={SIGMA}, n={n} x {N_SEEDS} seeds")
    print(f"  ensemble root: {ENS_ROOT}\n")
    rows, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for k, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if k % 25 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    gate = _gate(rows)
    print(f"\ngates OK: {gate['overlap_rows']} DoE rows bit-exact; "
          f"max refit drift {gate['max_refit_drift']:.2e} < {REFIT_TOL:.0e}\n")
    keep25 = {r["instance"] for r in rows if r["instance_index"] < 25}
    results = [analyse(rows, keep25, "n=25 registered subset"),
               analyse(rows, None, f"n={n} power extension")]
    OUT.write_text(json.dumps(dict(
        ticket="Q68", status="Power extension of the PRIMARY in-region contrast (G2). "
                             "Reported ALONGSIDE n=25.",
        config=dict(dim=DIM, sigma=SIGMA, budget=BUDGET, q=Q, sesoi=SESOI,
                    ensemble_root=str(ENS_ROOT)),
        provenance=dict(git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                               capture_output=True, text=True).stdout.strip(),
                        argv=sys.argv, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        gate=gate, results=results, rows=rows), indent=1) + "\n")
    print(f"wrote {OUT}\n")
    for res in results:
        print(f"--- {res['label']} (n={res['n']})   "
              f"GP peak inside region: {res['gp_peak_inside_region_rate']:.0%}")
        for c in res["contrasts"]:
            v = ("BO better" if c["lo"] > 0 else
                 "DoE better" if c["hi"] < 0 else "not separated")
            print(f"    {c['name']:<38} DoE {c['doe_mean']:.4f} BO {c['bo_mean']:.4f}  "
                  f"{c['contrast']:+.4f} [{c['lo']:+.4f},{c['hi']:+.4f}]  "
                  f"p={c['wilcoxon_p']:.4f}  {v}  TOST:{c['tost_verdict']}")
        print()


if __name__ == "__main__":
    main()
