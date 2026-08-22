"""Q59 map re-score · does `doe`'s map failure survive when it does NOT screen?

Registered in ``docs/OPEN-QUESTIONS.md`` at commit 24b7bc4, **before this file existed**.
Tests at ``tests/test_q59_map_rescore.py``, written and watched fail first.

------------------------------------------------------------------------------------
THE CONFOUND, AND WHY ONLY THIS ARM CAN SEPARATE IT
------------------------------------------------------------------------------------
Part IV's screening result confounds three things at once: **screening**, **sub-box
confinement** and **3 rounds vs 1**. `results/q59-hartmann-no-screen.json` carries
`doe_unscreened` -- a half-fraction face-centred CCD on **all six** coordinates, 47 runs +
1 confirmation = exactly 48 -- which is the only classical arm in the repository with
variation on every axis. It is therefore the only available way to hold the budget and
the landscape fixed while turning the screen off.

------------------------------------------------------------------------------------
WHAT THE COMMITTED FILE ALREADY SETTLES, AND IT IS NOT WHAT THE QUESTION ASSUMED
------------------------------------------------------------------------------------
On REGRET the screen **helps**, at both sigma, decisively:

    sigma=0.25   doe_screened 0.5623   doe_unscreened 0.7685   +0.2062  p=6.44e-05
    sigma=0.10   doe_screened 0.5428   doe_unscreened 0.7502   +0.2074  p=1.38e-05

So the screen is not why `doe` loses to BO on regret; it is why `doe` is not further
behind. **Part IV's claim is a MAP claim**, and every arm in the committed file carries
only `rule_a` and `oracle_best` -- no design matrix, no posterior, no map metric. That is
the gap this runner fills, and it is the only reason regeneration is warranted.

------------------------------------------------------------------------------------
COMPARABILITY
------------------------------------------------------------------------------------
Scored through ``run_p6_families.map_row`` -- **imported, not reimplemented** -- on the
same 20,000-point Sobol grid at the same seed, against the same committed `tau_q` table.
So a row here is comparable to a row in `results/p6-families.json` cell for cell, which
is the whole point: `doe_unscreened`'s symmetric difference has to be readable against
the `doe` column Part IV already published.

------------------------------------------------------------------------------------
GATE
------------------------------------------------------------------------------------
The regenerated `rule_a` and `oracle_best` must reproduce the committed Q59 columns at
**|delta| = 0 exactly**. Q59's own gate against `d20-rescore.json` sits at
`worst_abs_delta = 0.0`, so there is a committed column to hold this to and no excuse for
a tolerance. A miss halts the run.
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Both imported, neither reimplemented. A second copy of the CCD construction would be a
# second experiment, and a second copy of `map_row` would not be comparable to Part IV.
_Q59 = _load("_q59", ROOT / "scripts" / "run_q59_hartmann_no_screen.py")
_P6 = _load("_p6", ROOT / "scripts" / "run_p6_families.py")

from boec.doe import run_doe_arm                                     # noqa: E402
from boec.norms import grid_r2, sobol_grid, sup_err                  # noqa: E402
from boec.replay import unit_bounds                                  # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import TorchEvaluator, _plug_in_yvar          # noqa: E402
from boec.designspace import gp_adapter                              # noqa: E402

OUT = ROOT / "results" / "q59-map-rescore.json"
CKPT = ROOT / "results" / "q59-map-rescore.ckpt.jsonl"
COMMITTED = ROOT / "results" / "q59-hartmann-no-screen.json"

FAMILY, DIM = "hartmann6", 6
SIGMAS = _Q59.SIGMAS
N_SEEDS = _Q59.N_SEEDS
GAMMAS = _P6.GAMMAS
GRID_N, GRID_SEED = _P6.GRID_N, _P6.GRID_SEED
ARMS = ("doe_screened", "doe_unscreened")


class GateMiss(RuntimeError):
    """The regenerated scalar missed its committed column. Not a tolerance question."""


def _committed_index() -> dict:
    doc = json.loads(COMMITTED.read_text())
    return {(r["sigma"], r["seed"]): r["arms"] for r in doc["rows"]}


def _yvar(Y: torch.Tensor, sigma_rel: float) -> torch.Tensor:
    """The plug-in observation variance, from the SAME function the evaluator uses.

    `run_doe_arm` and `run_unscreened_ccd` both discard the variance the evaluator
    returned (`Y, _ = evaluator.evaluate(X)`), so it has to be recovered here.
    `boec.torch_oracle._plug_in_yvar` is imported rather than re-derived precisely so
    this is the evaluator's own definition and not a second one that happens to agree --
    `yhat^2 * sigma_rel^2 + sigma_add^2`, floored at `sigma_add^2`.

    `sigma_add` is 0 for these arms: `Q59._oracle()` is `UnitScaled(Hartmann6())` and
    `TorchEvaluator` is constructed with `sigma_rel` alone, so the additive term is its
    default of 0 and the floor is non-binding.
    """
    import numpy as np
    return torch.from_numpy(
        _plug_in_yvar(Y.detach().cpu().numpy().astype(float), sigma_rel, 0.0))


def _campaigns(sigma: float, seed: int):
    """Both classical protocols at one (sigma, seed), each with a FRESH evaluator.

    Fresh because `evaluate` consumes the noise stream and the committed columns were
    produced with one evaluator per arm -- sharing one would change the observations and
    the gate would (correctly) fail.
    """
    oracle = _Q59._oracle()
    opt = float(oracle.optimum_value)
    b = _Q59._bounds()

    ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
    r = run_doe_arm(ev, b, truth=ev.truth, budget=_Q59.BUDGET, seed=seed)
    t = ev.truth(r.X_visited).double()
    screened = {
        "X": r.X_visited, "Y": r.Y_visited, "Yvar": _yvar(r.Y_visited, sigma),
        "rule_a": opt - float(_Q59.reported_best_curve(t, r.Y_visited)[-1]),
        "oracle_best": opt - float(t.max()),
        "kept_factors": list(r.kept_factors),
    }

    ev2 = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
    u = _Q59.run_unscreened_ccd(ev2, b, truth=ev2.truth, optimum_value=opt, seed=seed,
                                return_design=True)
    unscreened = {"X": u["X_all"], "Y": u["Y_all"],
                  "Yvar": _yvar(u["Y_all"], sigma),
                  "rule_a": u["rule_a"], "oracle_best": u["oracle_best"],
                  "kept_factors": None}
    return {"doe_screened": screened, "doe_unscreened": unscreened}, oracle


def _active_mask(kept) -> torch.Tensor:
    """Which coordinates the design actually varied.

    `doe_screened` pins 2 of 6; `doe_unscreened` varies all 6. Amendment B3 bites on the
    first and not on the second, and pretending otherwise would pin an axis the design
    did vary -- which is exactly the sub-box half of the confound.
    """
    if kept is None:
        return torch.ones(DIM, dtype=torch.bool)
    m = torch.zeros(DIM, dtype=torch.bool)
    for i in kept:
        m[int(i)] = True
    return m


def score(sigma: float, seed: int, index: dict) -> list[dict]:
    arms, oracle = _campaigns(sigma, seed)
    ref = index[(sigma, seed)]

    # GATE FIRST, before any expensive scoring: a miss means the regeneration is not the
    # committed campaign and nothing downstream of it is worth computing.
    for arm in ARMS:
        for col in ("rule_a", "oracle_best"):
            got, want = arms[arm][col], ref[arm][col]
            if abs(got - want) != 0.0:
                raise GateMiss(
                    f"{arm} sigma={sigma} seed={seed} {col}: regenerated {got!r} against "
                    f"committed {want!r}, |delta|={abs(got-want):.3e}. Q59's own gate is "
                    f"at 0.0; this is not a tolerance to widen.")

    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    orc_t = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
    with torch.no_grad():
        truth = orc_t.truth(grid).reshape(-1).double()

    taus = [_P6.tau_for(FAMILY, DIM, p) for p in
            sorted(_P6.registered_p(FAMILY, DIM), reverse=True)]

    rows = []
    for arm in ARMS:
        a = arms[arm]
        model = build_gp(a["X"], a["Y"], a["Yvar"], unit_bounds(DIM))
        mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

        class _M:
            def posterior_mean_and_sd(self, Z):
                return mean, sd

        m = _M()
        sigma_pred = ((sigma * mean).abs() ** 2).sqrt()
        active = _active_mask(a["kept_factors"])
        base = {"family": FAMILY, "dim": DIM, "sigma": sigma, "seed": seed, "arm": arm,
                "rule_a": a["rule_a"], "oracle_best": a["oracle_best"],
                "n_active": int(active.sum()), "screened": arm == "doe_screened",
                "sup_err": sup_err(m, lambda Z: truth, grid),
                "grid_r2": grid_r2(m, lambda Z: truth, grid)}
        for t in taus:
            for gamma in GAMMAS:
                r = _P6.map_row(m, grid, truth, tau=t.tau, gamma=gamma,
                                sigma_pred=sigma_pred, active=active)
                ceiling = _P6.above_ceiling(t.tau, gamma, sigma)
                if ceiling:
                    r["degenerate"] = r["degenerate"] + ["above_ceiling"]
                rows.append({**base, "p": t.p, "tau": t.tau,
                             "tau_max": _P6.tau_max(gamma, sigma),
                             "tau_above_ceiling": ceiling,
                             "tau_source": "results/p5-tau-quantile.json", **r})
        del model, mean, sd
        gc.collect()
    del grid, truth
    gc.collect()
    return rows


def _provenance(argv, elapsed: float) -> dict:
    import botorch, gpytorch, numpy, scipy                           # noqa: E401
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                         text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip())
    return {"git_sha": sha, "git_dirty": dirty, "argv": argv,
            "elapsed_s": round(elapsed, 1), "python": sys.version.split()[0],
            "torch": torch.__version__, "botorch": botorch.__version__,
            "gpytorch": gpytorch.__version__, "numpy": numpy.__version__,
            "scipy": scipy.__version__, "threads": torch.get_num_threads(),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS")}


def read_ckpt(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="seeds per sigma")
    ap.add_argument("--ckpt", type=Path, default=CKPT)
    args = ap.parse_args()

    index = _committed_index()
    n = args.limit or N_SEEDS
    jobs = [(s, seed) for s in SIGMAS for seed in range(n)]
    done = {(e["sigma"], e["seed"]) for e in read_ckpt(args.ckpt)}
    t0 = time.time()

    print(f"Q59 MAP RE-SCORE · {FAMILY} d={DIM} · arms={ARMS}")
    print(f"  sigmas={SIGMAS} seeds={n} · {len(jobs)} campaigns · already done={len(done)}")
    print(f"  gamma={GAMMAS} · tau from results/p5-tau-quantile.json")
    print(f"  scored through run_p6_families.map_row -- comparable to p6-families.json")
    print(f"  GATE: rule_a and oracle_best at |delta| = 0 against the committed Q59 column")
    print(f"  threads={torch.get_num_threads()} OMP={os.environ.get('OMP_NUM_THREADS')}",
          flush=True)

    n_new = 0
    with args.ckpt.open("a") as fh:
        for k, (sigma, seed) in enumerate(jobs, 1):
            if (sigma, seed) in done:
                continue
            t = time.time()
            rows = score(sigma, seed, index)
            fh.write(json.dumps({"sigma": sigma, "seed": seed, "rows": rows}) + "\n")
            fh.flush()
            n_new += 1
            el = time.time() - t0
            print(f"  [{k:3d}/{len(jobs)}] sigma={sigma} seed={seed} {len(rows)} rows "
                  f"({time.time()-t:.1f}s) ~{el/max(n_new,1)*(len(jobs)-k)/60:.1f} min left",
                  flush=True)

    entries = read_ckpt(args.ckpt)
    rows = [r for e in entries for r in e["rows"]]
    work = Path(str(OUT) + ".partial")
    work.write_text(json.dumps({
        "status": "COMPLETE" if len(entries) >= len(jobs) else "PARTIAL",
        "keys_present": len(entries), "keys_expected": len(jobs),
        "provenance": _provenance(sys.argv, time.time() - t0),
        "config": {"family": FAMILY, "dim": DIM, "sigmas": list(SIGMAS),
                   "n_seeds": n, "arms": list(ARMS), "gammas": list(GAMMAS),
                   "grid_n": GRID_N, "grid_seed": GRID_SEED,
                   "gate": "rule_a and oracle_best at |delta| = 0 against "
                           "results/q59-hartmann-no-screen.json",
                   "scored_by": "run_p6_families.map_row, imported -- rows are "
                                "comparable to results/p6-families.json cell for cell",
                   "regret_note": "the screen HELPS on regret (+0.2062 at sigma=0.25, "
                                  "+0.2074 at sigma=0.10, both p<1e-4); this file scores "
                                  "the MAP, which is where Part IV's claim lives",
                   "d8_note": "an unscreened classical pipeline is arithmetically "
                              "impossible at d=8 within 48 wells (45 second-order terms, "
                              "no face-centred CCD lands on 48), so Part IV's d=8 cells "
                              "can never have this confound isolated"},
        "rows": rows}, indent=1))
    print(f"\n{len(entries)} campaigns · {len(rows)} rows -> {work.name}", flush=True)


if __name__ == "__main__":
    main()
