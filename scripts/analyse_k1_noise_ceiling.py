"""K1 -- the noise-ceiling check, docs/ODIN-VERDICT.md sec 6 K1, registered at
docs/SPADE-CALIBRATION-FIX-SPEC.md sec 2.

Grants `versionb`'s campaigns the TRUE noise variance (computed from the true f(x), not
the noisy reading `_plug_in_yvar` normally uses) and re-scores rule-P regret with
`run_fix1_terminal_rule.py`'s exact machinery (same GP fit, same locator settings). This
is a CEILING, not an estimate -- replicates give you an estimate OF sigma, not sigma
itself, so if even perfect knowledge of sigma does not move regret by >=0.01, no
finite-replicate scheme can either, and Piece A is not worth building regardless of K0.

No new campaigns: reuses `run_fix1_terminal_rule._observations` (X, Y construction)
read-only, substitutes only Yvar, re-uses the already-committed regret_p (plug-in Yvar)
from results/fix1-terminal-rule.json as the baseline -- no need to re-fit that side.

    .venv/bin/python scripts/analyse_k1_noise_ceiling.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch
from scipy.stats import wilcoxon

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import gp_adapter                    # noqa: E402
from boec.metrics import grid_screened_argmax               # noqa: E402
from boec.norms import sobol_grid                            # noqa: E402
from boec.replay import instance_by_id                       # noqa: E402
from boec.surrogate import build_gp                           # noqa: E402
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar   # noqa: E402


def _mod(alias: str, filename: str):
    spec = importlib.util.spec_from_file_location(alias, ROOT / "scripts" / filename)
    m = importlib.util.module_from_spec(spec)
    sys.modules[alias] = m
    spec.loader.exec_module(m)
    return m


FIX1 = _mod("_k1_fix1", "run_fix1_terminal_rule.py")

DIM, SIGMA = FIX1.DIM, FIX1.SIGMA
GRID_N, GRID_SEED = FIX1.GRID_N, FIX1.GRID_SEED
N_RESTARTS, RAW_SAMPLES, LOCATOR_SEED = FIX1.N_RESTARTS, FIX1.RAW_SAMPLES, FIX1.LOCATOR_SEED

COMMITTED = ROOT / "results" / "fix1-terminal-rule.json"
OUT = ROOT / "results" / "k1-noise-ceiling.json"


def committed_versionb() -> dict:
    d = json.loads(COMMITTED.read_text())
    rows = d["rows"] if isinstance(d, dict) else d
    return {(r["instance"], r["seed"]): r for r in rows if r["arm"] == "versionb"}


def one(inst_id: str, seed: int, committed_ref: dict) -> dict:
    """Regenerates X, Y directly via `_VB._two_plate(..., mode="lse")` -- NOT via
    `FIX1._observations`, which calls `_two_plate(orc, DIM, seed, mu_max, True)` and
    unpacks 3 return values. That call site predates `_two_plate`'s current signature
    (`mode: str`, returns 4 values `(X, Y, Yvar, diag)`, added in commit c8347f1) and
    raises `ValueError: too many values to unpack` if actually run today -- a real,
    previously-undetected regeneration break between two already-frozen files, not a
    bug in this script. `run_fix1_terminal_rule.py` is not edited (frozen); this script
    routes around it and separately verifies `regret_a` still matches the committed
    value below, so the campaign this analysis scores is provably the same one
    `fix1-terminal-rule.json`'s committed regret_p was computed from.
    """
    inst = instance_by_id(inst_id, DIM)
    mu_max = float(inst.optimum_value)
    bounds = FIX1.unit_bounds(DIM)
    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    orc_t = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    orc = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)

    X, Y, Yvar_plugin, _diag = FIX1._VB._two_plate(orc, DIM, seed, mu_max, mode="lse")
    with torch.no_grad():
        regret_a = float(mu_max - FIX1.scored_curve(orc_t, X, Y)[-1])

    ref = committed_ref[(inst_id, seed)]
    gate_delta = abs(regret_a - ref["regret_a"])
    if gate_delta > 0.0:
        return {"instance": inst_id, "seed": seed, "GATE_FAILED": True,
                "regenerated_regret_a": regret_a, "committed_regret_a": ref["regret_a"],
                "gate_abs_delta": gate_delta}

    with torch.no_grad():
        truth_X = orc_t.truth(X).reshape(-1).double().numpy()
    Yvar_true = torch.from_numpy(
        _plug_in_yvar(truth_X, SIGMA, orc.sigma_add)).reshape(Yvar_plugin.shape).to(Yvar_plugin.dtype)

    model = build_gp(X, Y, Yvar_true, bounds)

    def predict(Z: torch.Tensor, _m=model) -> torch.Tensor:
        with torch.no_grad():
            return _m.posterior(Z).mean

    grid_mean, _ = gp_adapter(model).posterior_mean_and_sd(grid)
    r = grid_screened_argmax(predict, grid, grid_mean, bounds,
                             n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES, seed=LOCATOR_SEED)
    with torch.no_grad():
        regret_p_true_sigma = float(mu_max - orc_t.truth(r.x.reshape(1, -1)))

    return {"instance": inst_id, "seed": seed, "GATE_FAILED": False,
            "regret_p_plugin": ref["regret_p"], "regret_p_true_sigma": regret_p_true_sigma,
            "ceiling_improvement": ref["regret_p"] - regret_p_true_sigma}


def main() -> None:
    committed_ref = committed_versionb()
    keys = sorted(committed_ref.keys(), key=lambda k: k[1])
    rows, t0 = [], time.time()
    for i, (inst_id, seed) in enumerate(keys):
        row = one(inst_id, seed, committed_ref)
        if row["GATE_FAILED"]:
            raise SystemExit(f"GATE FAILED at seed={seed}: regenerated regret_a="
                             f"{row['regenerated_regret_a']} vs committed "
                             f"{row['committed_regret_a']} (delta={row['gate_abs_delta']}) "
                             "-- a single failure aborts, per this project's convention")
        rows.append(row)
        print(f"[{i+1:2d}/{len(keys)}] seed={seed:<3d} "
              f"ceiling_improvement={rows[-1]['ceiling_improvement']:+.5f} "
              f"({(time.time()-t0)/60:.1f}m)", flush=True)

    improvements = np.array([r["ceiling_improvement"] for r in rows])
    stat, p = wilcoxon(improvements)
    rng = np.random.default_rng(0)
    boots = np.array([improvements[rng.integers(0, len(improvements), len(improvements))].mean()
                      for _ in range(4000)])
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])
    mean_improvement = float(improvements.mean())

    verdict = ("KILL -- ceiling improvement < 0.01; drop replicates, Piece A not worth "
               "building" if mean_improvement < 0.01 else
               "OPEN -- ceiling improvement >= 0.01; replicates COULD help, if an estimator "
               "gets close enough to the ceiling (K1 bounds the best case, not the "
               "achievable case)")

    out = {"n_campaigns": len(rows), "mean_ceiling_improvement": mean_improvement,
           "wilcoxon_p": float(p), "bootstrap_ci_95": [float(ci_lo), float(ci_hi)],
           "verdict": verdict, "rows": rows,
           "spec": "docs/SPADE-CALIBRATION-FIX-SPEC.md sec 2"}
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nmean ceiling improvement: {mean_improvement:+.5f} "
          f"[{ci_lo:+.5f}, {ci_hi:+.5f}], wilcoxon p={p:.4g}")
    print(verdict)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
