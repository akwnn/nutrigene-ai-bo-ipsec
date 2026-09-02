"""Fix 1 — re-score every committed campaign under a POSTERIOR-MEAN terminal rule.

    .venv/bin/python scripts/run_fix1_terminal_rule.py                 # all 10 arms
    .venv/bin/python scripts/run_fix1_terminal_rule.py --limit 2       # smoke
    .venv/bin/python scripts/run_fix1_terminal_rule.py --gate-only     # reproduce and stop

Registered in `docs/OPEN-QUESTIONS.md` (commit 4e14769) **before this file existed**.

WHAT IS ACTUALLY BEING ASKED
----------------------------
Every regret number in this study is **rule A**: `reported_best_curve` nominates the well
with the best *noisy* reading and scores the truth there. That rule **ignores the
surrogate entirely**, so an arm whose predictive map scores AUC 0.71-0.89 (`versionb`) and
one that scores 0.57-0.65 (`doe`) are scored as though neither had a model.

**Rule P** gives every arm the same posterior-mean terminal rule and asks whether the
ordering changes. The claim under test is an *asymmetry* — that reading the model helps
the arm with the better model more.

WHY THAT IS NOT ALREADY IMPLIED BY THE AUC GAP
-----------------------------------------------
K6 measured `grid_r2` **negative for every arm**, -0.1756 (`lhs`) to -6.1883 (`doe`): every
arm's posterior mean is a worse point predictor of `f` than the constant grid mean of `f`.
Negative R^2 says the **level** is mis-scaled. AUC says the **ranking** is fine. An argmax
needs only the ranking, and a badly mis-scaled surface can still put its maximum in the
right place. So the asymmetry is neither implied nor excluded by K6, and it is measured
here rather than asserted.

NO NEW CAMPAIGNS
----------------
Every arm is a *regeneration* of a committed campaign, gated against its committed
`regret` column at **|delta| = 0 exactly** before any rule-P number is read. K1
(`results/k1-replay-gate.json`) measured `doe`/`qlogei`/`qlognei` at worst |delta| 0.0 over
500 rows, so exact is the measured bar, not an aspiration. **No tolerance is introduced;**
a single failure aborts.

ONE LOCATOR, ONE SETTING, EVERY ARM  (T1.4c)
---------------------------------------------
This project has already shipped a locator asymmetry: Q29's BO arm located its rule-C
recommendation with `optimize_acqf(PosteriorMean)` at `num_restarts=10, raw_samples=256`
**unseeded** while its DoE arm used `constrained_argmax` at `20 / 4096` seeded — a 16x
screening gap that flatters whichever arm got the bigger screen (`tests/test_q29_locator.py`).
Here **every** arm goes through one `boec.metrics.grid_screened_argmax` call at one
setting: the registered 20,000-point Sobol grid at seed 0, then `constrained_argmax` at
`n_restarts=20, raw_samples=4096` — the two constants `boec.spread_gp` records as
load-bearing, so these numbers are commensurable with every rule-C figure already on disk.

NOT A Q29 RERUN. Q29 scores each method at **its own** recommender (DoE's stage-4 RSM
point against BO's GP posterior mean). Fix 1 fits **the same GP to every arm's wells** and
applies **one** terminal rule, so the only thing that varies between arms is the design.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import gp_adapter                              # noqa: E402
from boec.metrics import grid_screened_argmax                        # noqa: E402
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import (instance_by_id, regenerate, scored_curve,   # noqa: E402
                         unit_bounds)
from boec.runner import static_design                                # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402

DIM, SIGMA, BUDGET = 6, 0.25, 48
GRID_N, GRID_SEED = 20_000, 0
#: `boec.spread_gp`'s constants, and `constrained_argmax`'s defaults. Load-bearing:
#: changing either makes this incomparable with every rule-C number already committed.
N_RESTARTS, RAW_SAMPLES = 20, 4096
#: The locator's Sobol seed. Equal to GRID_SEED on purpose -- at a shared seed the
#: polish's 4,096-point screen IS the first 4,096 rows of the 20,000-point grid, so the
#: grid is a strict superset of the screen rather than an unrelated draw.
LOCATOR_SEED = GRID_SEED

ARMS = ("doe", "lhs", "sobol", "random", "qlogei", "qlognei",
        "qlogei-add", "qlogei-addonly", "plate1_only", "versionb")
#: Reported because Fix 1 changes nothing about how many rounds an arm spends, and every
#: contrast here is at equal WELLS only. Version B's own runner records the same mapping.
ROUNDS = {"doe": 3, "lhs": 1, "sobol": 1, "random": 1, "qlogei": 10, "qlognei": 10,
          "qlogei-add": 10, "qlogei-addonly": 10, "plate1_only": 1, "versionb": 2}

#: Which committed artefact carries each arm's rule-A column. Q30's kernel arms have no
#: E2 column -- K6 is the committed artefact that carries their regret; `plate1_only` and
#: `versionb` live in Version B's file. See the registration for the full table.
E2_GRID = ROOT / "results" / "e2-grid.json"
K6 = ROOT / "results" / "k6-designspace.json"
VERSIONB = ROOT / "results" / "versionb.json"
OUT = ROOT / "results" / "fix1-terminal-rule.json"

#: Exact. K1 measured every gated arm at worst |delta| = 0.0; `plate1_only` and `versionb`
#: were checked at 0.0 on a 3-key pre-flight before the registration was written.
GATE_TOL = 0.0

#: `run_versionb.py`'s two-plate builder, imported rather than reimplemented: a second
#: copy of plate 2's LSE selection would be a second campaign, and its regret could not be
#: gated against the committed one (D12).
_VB = importlib.util.module_from_spec(
    importlib.util.spec_from_file_location("_run_versionb",
                                           ROOT / "scripts" / "run_versionb.py"))
_VB.__spec__.loader.exec_module(_VB)


def _rows(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d if isinstance(d, list) else d.get("rows", d)


@lru_cache(maxsize=1)
def committed_column() -> dict[tuple[str, int, str], tuple[float, str]]:
    """``(instance, seed, arm) -> (committed regret, which file it came from)``."""
    out: dict[tuple[str, int, str], tuple[float, str]] = {}
    for r in _rows(E2_GRID):
        if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12 and r["arm"] in ARMS:
            out[(r["instance"], int(r["seed"]), r["arm"])] = (float(r["regret"]),
                                                              "e2-grid.json")
    for r in _rows(K6):
        if r["arm"] in ("qlogei-add", "qlogei-addonly"):
            out[(r["instance"], int(r["seed"]), r["arm"])] = (float(r["regret"]),
                                                              "k6-designspace.json")
    for r in _rows(VERSIONB):
        if r["arm"] in ("plate1_only", "versionb"):
            out[(r["instance"], int(r["seed"]), r["arm"])] = (float(r["regret"]),
                                                              "versionb.json")
    return out


def _observations(arm: str, inst_id: str, seed: int, orc, orc_t, mu_max: float):
    """``(X, Y, Yvar, rule_a)`` for one committed campaign, regenerated.

    **The rule-A regret comes back with the observations, and is not recomputed here.**
    It is the gate, so it has to be produced by the arithmetic the committed column was
    produced by, and for the spread arms that is not the same as scoring one curve:
    `run_e2.static_curve` averages 20 orderings whose final values are all identical, and
    the float64 mean of 20 copies of x is not bitwise x. `boec.replay.regenerate`
    reproduces that averaging deliberately (see its module docstring). Scoring a single
    curve here instead missed the committed `lhs` and `random` columns by 3.3e-16 and
    2.2e-16 and fired the gate on an arithmetic artefact of THIS script. The repair is to
    match the committed arithmetic, never to raise the tolerance.

    `plate1_only` and `versionb` are Version B's arms and `run_versionb.py` scores them
    with a single `scored_curve` call, so that is what they get.
    """
    if arm == "plate1_only":
        X = static_design(unit_bounds(DIM), "lhs", BUDGET, seed)
        Y, V = orc.evaluate(X)
    elif arm == "versionb":
        X, Y, V = _VB._two_plate(orc, DIM, seed, mu_max, True)
    else:
        rec = regenerate(inst_id, DIM, SIGMA, seed, arm)
        return rec.X, rec.Y, rec.Yvar, rec.regret
    return X, Y, V, float(mu_max - scored_curve(orc_t, X, Y)[-1])


def one(job: tuple[str, int, tuple[str, ...]]) -> list[dict]:
    """Every arm for one ``(instance, seed)``. The grid and the truth are built once."""
    inst_id, seed, arms = job
    inst = instance_by_id(inst_id, DIM)
    mu_max = float(inst.optimum_value)
    bounds = unit_bounds(DIM)
    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    #: A separate oracle for scoring, so `truth` is never read off an oracle whose noise
    #: stream a regeneration is still consuming.
    orc_t = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    committed = committed_column()

    rows = []
    for arm in arms:
        t0 = time.time()
        orc = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
        X, Y, Yvar, regret_a = _observations(arm, inst_id, seed, orc, orc_t, mu_max)

        # --- rule A: the gate, not a new number -----------------------------------
        ref, src = committed[(inst_id, seed, arm)]
        delta = abs(regret_a - ref)

        # --- rule P: one model, one locator, every arm -----------------------------
        model = build_gp(X, Y, Yvar, bounds)

        def predict(Z: torch.Tensor, _m=model) -> torch.Tensor:
            with torch.no_grad():
                return _m.posterior(Z).mean

        # CHUNKED. 20k points through `model.posterior` in one call is 100.6s and a
        # 3.2 GB joint covariance whose off-diagonal is never used.
        grid_mean, _ = gp_adapter(model).posterior_mean_and_sd(grid)
        r = grid_screened_argmax(predict, grid, grid_mean, bounds,
                                 n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES,
                                 seed=LOCATOR_SEED)
        with torch.no_grad():
            regret_p = float(mu_max - orc_t.truth(r.x.reshape(1, -1)))
            regret_p_grid = float(mu_max - orc_t.truth(r.x_grid.reshape(1, -1)))

        rows.append({
            "instance": inst_id, "seed": seed, "arm": arm, "dim": DIM, "sigma": SIGMA,
            "rounds": ROUNDS[arm], "n_wells": int(X.shape[0]),
            "optimum_value": mu_max,
            "regret_a": regret_a, "regret_a_committed": ref, "gate_source": src,
            "gate_abs_delta": delta,
            "regret_p": regret_p, "regret_p_grid": regret_p_grid,
            "improvement": regret_a - regret_p,
            "post_mean_at_x_p": r.value, "post_mean_at_x_grid": r.value_grid,
            "from_grid": bool(r.from_grid),
            "n_starts_converged": int(r.n_starts_converged),
            "x_p": [float(v) for v in r.x],
            "secs": round(time.time() - t0, 2),
        })
        del model, grid_mean
        gc.collect()
    return rows


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import numpy
    import scipy
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def _config() -> dict:
    return {"dim": DIM, "sigma": SIGMA, "budget": BUDGET, "arms": list(ARMS),
            "rounds": ROUNDS, "grid_n": GRID_N, "grid_seed": GRID_SEED,
            "n_restarts": N_RESTARTS, "raw_samples": RAW_SAMPLES,
            "locator_seed": LOCATOR_SEED, "gate_tol": GATE_TOL,
            "rule_a": "optimum_value - truth(argmax observed Y)",
            "rule_p": ("optimum_value - truth(argmax posterior mean), located on the "
                       f"{GRID_N}-point Sobol grid at seed {GRID_SEED} and polished with "
                       f"constrained_argmax(n_restarts={N_RESTARTS}, "
                       f"raw_samples={RAW_SAMPLES}, seed={LOCATOR_SEED})")}


def _write(rows: list[dict], gate_fail: list[dict], argv) -> None:
    OUT.write_text(json.dumps({"provenance": _provenance(argv), "config": _config(),
                               "gate": {"tol": GATE_TOL, "rows_checked": len(rows),
                                        "worst_abs_delta": max(
                                            (r["gate_abs_delta"] for r in rows),
                                            default=0.0),
                                        "failures": gate_fail},
                               "rows": rows}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None,
                    help="(instance, seed) pairs to run; default all 50")
    ap.add_argument("--arms", type=str, default=None, help="comma-separated subset")
    ap.add_argument("--gate-only", action="store_true",
                    help="regenerate and gate; write nothing")
    args = ap.parse_args()

    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    committed = committed_column()
    keys = sorted({(r["instance"], int(r["seed"])) for r in _rows(E2_GRID)
                   if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12
                   and r["arm"] == "qlogei"})
    if args.limit:
        keys = keys[:args.limit]

    missing = [(i, s, a) for (i, s) in keys for a in arms
               if (i, s, a) not in committed]
    if missing:
        raise SystemExit(f"no committed column for {len(missing)} (instance, seed, arm) "
                         f"combinations, first {missing[:3]} -- refusing to run ungated")

    print(f"Fix 1 · posterior-mean terminal rule · HEAD={_provenance(sys.argv)['git_sha']}")
    print(f"cell d={DIM} sigma={SIGMA} · {len(keys)} (instance, seed) x {len(arms)} arms "
          f"= {len(keys)*len(arms)} campaigns")
    print(f"rule P: {GRID_N}-pt Sobol grid seed {GRID_SEED}, polished at "
          f"n_restarts={N_RESTARTS} raw_samples={RAW_SAMPLES} seed={LOCATOR_SEED}")
    print(f"gate: committed rule-A regret must reproduce at |delta| = {GATE_TOL:g} "
          f"EXACTLY\n", flush=True)

    done: list[dict] = []
    if OUT.exists() and not args.gate_only:
        done = json.loads(OUT.read_text())["rows"]
        print(f"  resuming — {len(done)} rows already on disk")
    have = {(r["instance"], r["seed"], r["arm"]) for r in done}

    jobs = [(i, s, tuple(a for a in arms if (i, s, a) not in have)) for (i, s) in keys]
    jobs = [j for j in jobs if j[2]]

    t0 = time.time()
    gate_fail: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for k, batch in enumerate(pool.map(one, jobs), 1):
            done.extend(batch)
            for r in batch:
                if r["gate_abs_delta"] > GATE_TOL:
                    gate_fail.append({key: r[key] for key in
                                      ("instance", "seed", "arm", "regret_a",
                                       "regret_a_committed", "gate_abs_delta",
                                       "gate_source")})
                    print(f"  !! GATE {r['arm']} {r['instance']} seed={r['seed']} "
                          f"|delta|={r['gate_abs_delta']:.3e} vs {r['gate_source']}",
                          flush=True)
            if not args.gate_only:
                _write(done, gate_fail, sys.argv)
            el = time.time() - t0
            print(f"  [{k:3d}/{len(jobs)}] {batch[0]['instance']} seed={batch[0]['seed']}"
                  f"  {el/60:5.1f} min elapsed, ~{el/k*(len(jobs)-k)/60:5.1f} min left",
                  flush=True)

    worst = max((r["gate_abs_delta"] for r in done), default=0.0)
    print(f"\n  gate: {len(done)} rows checked, worst |delta| = {worst:.3e}, "
          f"{len(gate_fail)} failures")
    if gate_fail:
        print("\n*** STOP. A regenerated campaign is not the committed campaign, so the "
              "rule-P column beside it describes a different experiment. Reported, not "
              "worked around. ***")
        raise SystemExit(1)
    if args.gate_only:
        return
    print(f"  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.0f} min)")


if __name__ == "__main__":
    main()
