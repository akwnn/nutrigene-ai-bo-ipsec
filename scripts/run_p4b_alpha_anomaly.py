"""P4b — `alpha*` ranks the arms backwards. Is posterior width the reason?

    .venv/bin/python scripts/run_p4b_alpha_anomaly.py --limit 2      # smoke
    .venv/bin/python scripts/run_p4b_alpha_anomaly.py                # all 9 arms x 50

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) **before this file existed**.

THE ANOMALY, MEASURED FIRST AND STATED BEFORE IT IS EXPLAINED
--------------------------------------------------------------
At tau_frac = 0.75 the mean `alpha_star` of the three spread arms runs

    random 0.6521  >  lhs 0.6291  >  sobol 0.5275

and their committed regret at the same cell runs

    lhs 0.1270  <  sobol 0.1724  <  random 0.2216

— very nearly the reverse. And `doe`, whose posterior mean is a worse predictor of the
response than the constant grid mean (`grid_r2` = **-6.19**, the worst in the project),
scores `alpha_star` = **1.0000** at tau_frac = 0.60, the largest value the statistic can
take. All four numbers are re-measured from the committed files by
`tests/test_p4b_alpha_anomaly.py` rather than carried forward in prose.

THE HYPOTHESIS UNDER TEST, NOT ASSUMED
---------------------------------------
`alpha_star` is the largest confidence at which a **non-empty** conservative estimate
exists. A design that leaves large unsampled gaps buys a wider posterior, a more diffuse
Vorob'ev structure, and — on this reading — a higher `alpha_star`. That is: **the
statistic would be rewarding not knowing.** It is a hypothesis. It is tested here by
regressing `alpha_star` on the mean posterior sd over exactly the points the draws were
taken on, within arm and across arms.

THE REGISTERED DECISION RULE
-----------------------------
* Spearman rho of `alpha_star` against regret across the 9 arms **<= -0.5 with a CI
  excluding 0** -> `alpha_star` is confirmed anti-correlated with the validated metric,
  and **every table in this project carrying `alpha_star` must carry that fact**.
* **CI includes 0** -> reported as an unexplained anomaly, recorded and not smoothed, in
  the manner of `docs/METHODS.md:583`.

THE CELL THE REGISTRATION DID NOT NAME
---------------------------------------
It states the anomaly at tau_frac = 0.75 (the three-way spread-arm inversion) and at 0.60
(`doe` at the maximum) but does not say which cell the decision is read at. **tau_frac =
0.75 is declared primary here**, because it is the cell whose ranking the registration
actually states, and all four cells are reported with Holm across them. Choosing after
seeing four coefficients would be the thing pre-registration exists to prevent, so the
choice is recorded here and in the output `config`.

METRIC STATUS TRAVELS WITH THE ANSWER
--------------------------------------
`alpha_star` is MODEL-INTERNAL: a functional of the fitted posterior and nothing else.
Regret is VALIDATED: it consults the noiseless oracle. Per the registration a validated
metric beats a model-internal one and the disagreement is reported — so a negative rho
here is not a defect in regret.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch
from scipy.stats import spearmanr, wilcoxon

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import gp_adapter                              # noqa: E402
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import CampaignRecord, regenerate, unit_bounds      # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402

DIM, SIGMA = 6, 0.25
#: K6b's subset and seed. `alpha_star` was computed on draws over exactly these points,
#: so the width regressed against it is measured on exactly these points.
SUBSET_N, GRID_SEED = 2_000, 0
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
#: Declared before the coefficients were seen. See the module docstring.
PRIMARY_TAU_FRAC = 0.75

#: Nine, because P4 added the ninth. Eight is the failure mode this task exists to avoid.
ARMS = ("coord", "doe", "lhs", "qlogei", "qlogei-add", "qlogei-addonly", "qlognei",
        "random", "sobol")

E2_GRID = ROOT / "results" / "e2-grid.json"
K6 = ROOT / "results" / "k6-designspace.json"
K6B = ROOT / "results" / "k6b-conservative.json"
K6B_SPREAD = ROOT / "results" / "k6b-conservative-spread.json"
P4_COORD = ROOT / "results" / "p4-coord.json"
OUT = ROOT / "results" / "p4b-alpha-star-anomaly.json"

GATE_TOL = 0.0
N_BOOT, BOOT_SEED = 4_000, 0
SESOI = 0.02
#: The registered threshold. Never moved to make a verdict come out.
RHO_THRESHOLD = -0.5


# ======================================================================================
# COMMITTED COLUMNS
# ======================================================================================

def _rows(path: Path, key: str = "rows") -> list[dict]:
    d = json.loads(path.read_text())
    if isinstance(d, list):
        return d
    return d[key]


def committed_regret() -> dict[tuple[str, int, str], tuple[float, str]]:
    """``(instance, seed, arm) -> (regret, source file)``. Fix 1's table, plus `coord`.

    The kernel arms have no `e2-grid.json` column — `k6-designspace.json` is the
    committed artefact that carries their regret, and that is the file Fix 1 gated them
    against too.
    """
    out: dict[tuple[str, int, str], tuple[float, str]] = {}
    for r in _rows(E2_GRID):
        if (r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12 and r["arm"] in ARMS):
            out[(r["instance"], int(r["seed"]), r["arm"])] = (float(r["regret"]),
                                                              "e2-grid.json")
    for r in _rows(K6):
        if r["arm"] in ("qlogei-add", "qlogei-addonly"):
            out[(r["instance"], int(r["seed"]), r["arm"])] = (float(r["regret"]),
                                                              "k6-designspace.json")
    return out


def committed_alpha_star() -> dict[tuple[str, int, str, float], float]:
    """``(instance, seed, arm, tau_frac) -> alpha_star``, from the committed K6b files.

    **Not recomputed.** The draws that produced these are the committed ones; taking them
    again here would gate a regeneration against a regeneration of itself (D12).
    """
    rows = _rows(K6B) + _rows(K6B_SPREAD)
    if P4_COORD.exists():
        rows += _rows(P4_COORD, "k6b_rows")
    return {(r["instance"], int(r["seed"]), r["arm"], float(r["tau_frac"])):
            float(r["alpha_star"]) for r in rows if r["arm"] in ARMS}


# ======================================================================================
# POSTERIOR WIDTH, MEASURED WHERE alpha* WAS
# ======================================================================================

def active_subspace_grid(rec: CampaignRecord, X_sub: torch.Tensor) -> torch.Tensor:
    """K6b's Amendment B3 construction: dropped coordinates pinned at their hold values.

    An arm that never varied a factor may not certify a range for it, so its region — and
    therefore its posterior width — is evaluated on the subset with every screened-out
    coordinate pinned to where the screen held it. An arm that varied every factor gets
    the subset untouched, and gets it back as the *same tensor*, not a copy.
    """
    if rec.kept_factors is None or not rec.dropped_held_at:
        return X_sub
    X = X_sub.clone()
    for j, v in rec.dropped_held_at.items():
        X[:, int(j)] = v
    return X


@lru_cache(maxsize=1)
def _p4():
    """P4's runner, imported once per worker process.

    Cached because importing it also imports K6's and K6b's runners; paying that on every
    one of 50 units would cost more than the `coord` regenerations themselves.
    """
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("_p4_coord", ROOT / "scripts" / "run_p4_coord.py")
    m = module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _regenerate(arm: str, instance: str, seed: int) -> CampaignRecord:
    """`coord` is not in `boec.replay`'s arm lists; P4's runner owns its regeneration."""
    if arm == "coord":
        return _p4().regenerate_coord(instance, DIM, SIGMA, seed)
    return regenerate(instance, DIM, SIGMA, seed, arm)


def _one(job: tuple[str, int, tuple[str, ...]]) -> list[dict]:
    """Every arm for one ``(instance, seed)``. The subset is built once."""
    instance, seed, arms = job
    X_sub = sobol_grid(DIM, SUBSET_N, seed=GRID_SEED)
    out = []
    for arm in arms:
        t0 = time.time()
        rec = _regenerate(arm, instance, seed)
        model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(DIM))
        X_eval = active_subspace_grid(rec, X_sub)
        mean, sd = gp_adapter(model).posterior_mean_and_sd(X_eval)
        out.append({
            "instance": instance, "seed": seed, "arm": arm, "regret": rec.regret,
            "n_active": DIM if rec.kept_factors is None else len(rec.kept_factors),
            "mean_posterior_sd": float(sd.mean()),
            "median_posterior_sd": float(sd.median()),
            "max_posterior_sd": float(sd.max()),
            "mean_posterior_mean": float(mean.mean()),
            "secs": round(time.time() - t0, 2)})
        del model, mean, sd
        gc.collect()
    return out


# ======================================================================================
# STATISTICS
# ======================================================================================

def _boot_ci(samples: np.ndarray) -> tuple[float, float]:
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def spearman_across_arms(data: dict[str, dict[tuple[str, int], tuple[float, float]]]
                         ) -> dict:
    """Spearman rho of arm-mean ``alpha_star`` against arm-mean regret, over the arms.

    Args:
        data: ``arm -> unit -> (alpha_star, regret)``. Every arm must carry every unit.

    The bootstrap resamples **units**, never arms. The nine points are means over the
    same 50 `(instance, seed)` pairs and the variability being estimated is theirs; an
    arm-level resample would estimate the wrong thing and, on any draw with duplicates,
    compute the coefficient over fewer than nine distinct arms.
    """
    arms = sorted(data)
    units = sorted(data[arms[0]])
    for a in arms:
        if sorted(data[a]) != units:
            raise ValueError(f"arm {a!r} does not carry the same units as {arms[0]!r}")

    alpha = np.array([[data[a][u][0] for u in units] for a in arms])   # (n_arms, n_units)
    regret = np.array([[data[a][u][1] for u in units] for a in arms])

    rho = float(spearmanr(alpha.mean(axis=1), regret.mean(axis=1)).statistic)

    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, len(units), size=(N_BOOT, len(units)))
    boots = np.empty(N_BOOT)
    for b in range(N_BOOT):
        take = idx[b]
        boots[b] = spearmanr(alpha[:, take].mean(axis=1),
                             regret[:, take].mean(axis=1)).statistic
    lo, hi = _boot_ci(boots)
    # Two-sided bootstrap p: twice the smaller tail mass on the far side of 0, floored at
    # 1/N_BOOT. Spearman's asymptotic p is not available — the coefficient is taken over
    # nine arm MEANS, not over independent observations — and a CI-derived indicator would
    # collapse the Holm step-down to two values.
    p = min(1.0, 2 * min(float(np.mean(boots >= 0)), float(np.mean(boots <= 0))))
    return {"rho": rho, "ci_lo": lo, "ci_hi": hi,
            "bootstrap_p": max(p, 1.0 / N_BOOT),
            "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "n_arms": len(arms), "n_units": len(units), "n_boot": N_BOOT,
            #: Constant by construction — the bootstrap resamples units, so every
            #: resample still ranks all of the arms. Recorded so that stays checkable.
            "n_arms_per_resample": len(arms),
            "arms": arms,
            "mean_alpha_star": {a: float(alpha[i].mean()) for i, a in enumerate(arms)},
            "mean_regret": {a: float(regret[i].mean()) for i, a in enumerate(arms)}}


def _ols(x: np.ndarray, y: np.ndarray) -> dict:
    """Slope, intercept and R-squared of ``y ~ x``. Degenerate x returns nan, not zero."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3 or float(np.std(x)) == 0.0:
        return {"slope": float("nan"), "intercept": float("nan"),
                "r2": float("nan"), "n": int(len(x))}
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"slope": float(slope), "intercept": float(intercept),
            "r2": float("nan") if ss_tot == 0 else float(1 - ss_res / ss_tot),
            "n": int(len(x))}


def _paired(name: str, a: np.ndarray, b: np.ndarray) -> dict:
    """Paired ``a - b`` over the 50 units. Wilcoxon governs yes/no, bootstrap magnitude."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, len(d), size=(N_BOOT, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = _boot_ci(means)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:                                               # all-zero differences
        p = float("nan")
    return {"contrast": name, "n": int(len(d)), "mean_diff": float(d.mean()),
            "ci_lo": lo, "ci_hi": hi, "p": p,
            "bootstrap_excludes_zero": bool(lo > 0 or hi < 0),
            "exceeds_sesoi": bool(abs(float(d.mean())) > SESOI)}


def spread_arm_inversion(width: dict, alpha: dict, units: list, tf: float) -> dict:
    """Is the three-way spread-arm inversion an ordering, or three means in a row?

    The registration states it as a ranking — `random` > `lhs` > `sobol` on alpha*, and
    the reverse on regret. A ranking of three means is not evidence that the underlying
    quantities are ordered. Each pair is therefore tested **paired over the same 50
    units**, on both axes, with Holm across the six contrasts. This is the registered
    statistics applied to the registered claim; the decision rule itself is unchanged and
    is still read off the rank correlation.
    """
    pairs = (("random", "lhs"), ("random", "sobol"), ("lhs", "sobol"))
    out = []
    for hi_arm, lo_arm in pairs:
        out.append(_paired(
            f"alpha*({hi_arm}) - alpha*({lo_arm})",
            np.array([alpha[(u[0], u[1], hi_arm, tf)] for u in units]),
            np.array([alpha[(u[0], u[1], lo_arm, tf)] for u in units])))
        out.append(_paired(
            f"regret({hi_arm}) - regret({lo_arm})",
            np.array([width[(u[0], u[1], hi_arm)]["regret"] for u in units]),
            np.array([width[(u[0], u[1], lo_arm)]["regret"] for u in units])))
    return {"tau_frac": tf, "contrasts": _holm(out),
            "note": ("A positive alpha* difference alongside a positive regret "
                     "difference for the same pair IS the inversion: the arm that scores "
                     "higher on the model-internal statistic is the one with more regret.")}


def _holm(entries: list[dict], key: str = "p") -> list[dict]:
    """Holm across the cells of this family. The family is the four tau_frac cells."""
    finite = [e for e in entries if np.isfinite(e[key])]
    order = sorted(range(len(finite)), key=lambda i: finite[i][key])
    k, running = len(finite), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (k - rank) * finite[i][key]))
        finite[i]["holm_p"] = running
        finite[i]["holm_sig_at_0.05"] = bool(running < 0.05)
    for e in entries:
        e.setdefault("holm_p", float("nan"))
        e.setdefault("holm_sig_at_0.05", False)
    return entries


def analyse(width_rows: list[dict], alpha: dict) -> dict:
    """Every registered quantity: the two regressions, the ranking rho, and the verdict."""
    width = {(r["instance"], r["seed"], r["arm"]): r for r in width_rows}
    units = sorted({(r["instance"], r["seed"]) for r in width_rows})
    arms = sorted({r["arm"] for r in width_rows})

    per_cell = {}
    for tf in TAU_FRACS:
        data = {a: {u: (alpha[(u[0], u[1], a, tf)], width[(u[0], u[1], a)]["regret"])
                    for u in units} for a in arms}
        rank = spearman_across_arms(data)

        # --- the hypothesis: alpha* is a functional of posterior WIDTH ---------------
        within = {}
        for a in arms:
            sd = np.array([width[(u[0], u[1], a)]["mean_posterior_sd"] for u in units])
            al = np.array([alpha[(u[0], u[1], a, tf)] for u in units])
            fit = _ols(sd, al)
            r = spearmanr(sd, al)
            fit["spearman_rho"] = float(r.statistic)
            fit["p"] = float(r.pvalue)
            within[a] = fit
        _holm(list(within.values()))

        sd_all = np.array([width[(u[0], u[1], a)]["mean_posterior_sd"]
                           for a in arms for u in units])
        al_all = np.array([alpha[(u[0], u[1], a, tf)] for a in arms for u in units])
        across = _ols(sd_all, al_all)
        r = spearmanr(sd_all, al_all)
        across["spearman_rho"] = float(r.statistic)
        across["p"] = float(r.pvalue)

        # --- arm-level: does a wider posterior buy a higher alpha* across designs? ---
        arm_sd = np.array([np.mean([width[(u[0], u[1], a)]["mean_posterior_sd"]
                                    for u in units]) for a in arms])
        arm_al = np.array([np.mean([alpha[(u[0], u[1], a, tf)] for u in units])
                           for a in arms])
        r_arm = spearmanr(arm_sd, arm_al)

        per_cell[tf] = {
            "tau_frac": tf,
            "rank_correlation_alpha_vs_regret": rank,
            "regression_alpha_on_sd_within_arm": within,
            "regression_alpha_on_sd_across_arms": across,
            "arm_level_sd_vs_alpha": {"spearman_rho": float(r_arm.statistic),
                                      "p": float(r_arm.pvalue), "n_arms": len(arms),
                                      "mean_posterior_sd":
                                          {a: float(arm_sd[i])
                                           for i, a in enumerate(arms)}},
            "spread_arm_inversion": spread_arm_inversion(width, alpha, units, tf),
            "p": rank["bootstrap_p"],
        }

    _holm([per_cell[tf] for tf in TAU_FRACS])

    prim = per_cell[PRIMARY_TAU_FRAC]["rank_correlation_alpha_vs_regret"]
    confirmed = prim["rho"] <= RHO_THRESHOLD and prim["ci_excludes_zero"]
    if confirmed:
        verdict = "ANTICORRELATED"
        wording = (
            f"alpha* is confirmed anti-correlated with the validated metric at the "
            f"primary cell: rho = {prim['rho']:.4f} [{prim['ci_lo']:.4f}, "
            f"{prim['ci_hi']:.4f}] over {prim['n_arms']} arms, at or below the "
            f"registered {RHO_THRESHOLD} with a CI excluding 0. EVERY TABLE IN THIS "
            f"PROJECT CARRYING alpha* MUST CARRY THAT FACT.")
    elif not prim["ci_excludes_zero"]:
        verdict = "UNEXPLAINED_ANOMALY"
        wording = (
            f"The CI includes 0 (rho = {prim['rho']:.4f} [{prim['ci_lo']:.4f}, "
            f"{prim['ci_hi']:.4f}]). The ranking is reported as an unexplained anomaly, "
            f"recorded and not smoothed, in the manner of docs/METHODS.md:583.")
    else:
        verdict = "NEGATIVE_BUT_ABOVE_THRESHOLD"
        wording = (
            f"rho = {prim['rho']:.4f} [{prim['ci_lo']:.4f}, {prim['ci_hi']:.4f}]: the CI "
            f"excludes 0 but rho does not reach the registered {RHO_THRESHOLD}. Neither "
            f"registered branch fires exactly; reported as measured, with the direction "
            f"stated and the strength not overclaimed.")

    return {"n_units": len(units), "n_arms": len(arms), "arms": arms,
            "primary_tau_frac": PRIMARY_TAU_FRAC,
            "per_tau_frac": {str(tf): per_cell[tf] for tf in TAU_FRACS},
            "decision": {"verdict": verdict, "wording": wording,
                         "rho_threshold": RHO_THRESHOLD,
                         "primary": prim,
                         "sesoi": SESOI}}


# ======================================================================================
# DRIVER
# ======================================================================================

def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__}


def _load_checkpoint(path: Path) -> list[dict]:
    """Rows already scored. Empty when there is no checkpoint or it is unreadable.

    Only units with a COMPLETE set of arms are kept: a half-written unit would leave the
    ranking uneven across arms, which `spearman_across_arms` rejects outright rather than
    silently averaging over different numbers of campaigns.
    """
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print(f"  checkpoint {path} is not readable JSON; starting over")
        return []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=1,
                   help="1 runs serially in-process. Higher spawns a pool, which this "
                        "machine kills under memory pressure -- see the checkpoint below.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--checkpoint", type=str,
                   default=str(Path(tempfile.gettempdir()) / "p4b-alpha-ckpt.json"),
                   help="scratch file of scored units, re-read on restart. NOT the "
                        "result: results/p4b-alpha-star-anomaly.json is written once, "
                        "whole, at the end.")
    args = ap.parse_args()

    if not P4_COORD.exists():
        raise SystemExit(
            "results/p4-coord.json is missing. P4b's ranking is registered at NINE arms "
            "and `coord` is the ninth; running eight and calling it nine is the failure "
            "this task exists to avoid. Run scripts/run_p4_coord.py first.")

    committed = committed_regret()
    alpha = committed_alpha_star()
    units = sorted({(k[0], k[1]) for k in alpha if k[2] == "qlogei"})
    if args.limit:
        units = units[:args.limit]

    missing = [(u, a, tf) for u in units for a in ARMS for tf in TAU_FRACS
               if (u[0], u[1], a, tf) not in alpha]
    if missing:
        raise SystemExit(f"no committed alpha_star for {len(missing)} cells, first "
                         f"{missing[:3]} -- refusing to run on a partial ranking")

    prov = _provenance(sys.argv)
    print(f"P4b · alpha* vs regret · HEAD={prov['git_sha']}")
    print(f"cell d={DIM} sigma={SIGMA} · {len(units)} units x {len(ARMS)} arms")
    print(f"alpha* read from the committed K6b files; posterior sd measured on the same "
          f"{SUBSET_N}-pt subset (seed {GRID_SEED})")
    print(f"primary tau_frac = {PRIMARY_TAU_FRAC}, declared before the coefficients were "
          f"seen; all four reported with Holm")
    print(f"gate: regenerated regret must reproduce its committed column at "
          f"|delta| = {GATE_TOL:g}\n", flush=True)

    ckpt = Path(args.checkpoint)
    unit_set = set(units)
    rows: list[dict] = [r for r in _load_checkpoint(ckpt)
                        if (r["instance"], r["seed"]) in unit_set and r["arm"] in ARMS]
    done = {(r["instance"], r["seed"]) for r in rows
            if sum(1 for x in rows
                   if (x["instance"], x["seed"]) == (r["instance"], r["seed"])) == len(ARMS)}
    rows = [r for r in rows if (r["instance"], r["seed"]) in done]
    jobs = [(u[0], u[1], ARMS) for u in units if u not in done]
    if rows:
        print(f"  resuming — {len(done)} units already on the checkpoint, "
              f"{len(jobs)} to go\n", flush=True)

    t0 = time.time()

    def _record(batch: list[dict], k: int) -> None:
        for r in batch:
            ref, src = committed[(r["instance"], r["seed"], r["arm"])]
            r["regret_committed"], r["gate_source"] = ref, src
            r["gate_abs_delta"] = abs(r["regret"] - ref)
            if r["gate_abs_delta"] > GATE_TOL:
                print(f"  !! GATE {r['arm']} {r['instance']} seed={r['seed']} "
                      f"|delta|={r['gate_abs_delta']:.3e}", flush=True)
        rows.extend(batch)
        ckpt.write_text(json.dumps(rows))
        el = time.time() - t0
        print(f"  [{k:3d}/{len(jobs)}] {batch[0]['instance']} "
              f"seed={batch[0]['seed']}  {el/60:5.1f} min elapsed, "
              f"~{el/k*(len(jobs)-k)/60:5.1f} min left", flush=True)

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, batch in enumerate(pool.map(_one, jobs), 1):
                _record(batch, k)
    else:
        # Serial, in-process. A pool worker killed by the OS takes every unwritten future
        # with it, and this machine kills them.
        for k, job in enumerate(jobs, 1):
            _record(_one(job), k)

    gate_failures = [{k_: r[k_] for k_ in
                      ("instance", "seed", "arm", "regret", "regret_committed",
                       "gate_abs_delta", "gate_source")}
                     for r in rows if r["gate_abs_delta"] > GATE_TOL]
    worst = max((r["gate_abs_delta"] for r in rows), default=0.0)
    print(f"\n  gate: {len(rows)} rows checked, worst |delta| = {worst:.3e}, "
          f"{len(gate_failures)} failures")
    if gate_failures:
        print("\n*** STOP. A regenerated campaign is not the committed campaign, so the "
              "posterior width beside it belongs to a different experiment. Reported, "
              "not worked around. ***")
        raise SystemExit(1)

    summary = analyse(rows, alpha)
    OUT.write_text(json.dumps({
        "provenance": prov,
        "config": {"dim": DIM, "sigma": SIGMA, "arms": list(ARMS),
                   "tau_fracs": list(TAU_FRACS),
                   "primary_tau_frac": PRIMARY_TAU_FRAC,
                   "primary_tau_frac_note": (
                       "The registration states the anomaly at tau_frac 0.75 (the "
                       "three-way spread-arm inversion) and 0.60 (doe at the maximum) "
                       "but does not name the cell the decision is read at. 0.75 is "
                       "declared primary here because it is the cell whose ranking the "
                       "registration states; all four are reported with Holm across "
                       "them. The choice is recorded rather than made after seeing the "
                       "coefficients."),
                   "subset_n": SUBSET_N, "grid_seed": GRID_SEED,
                   "n_boot": N_BOOT, "bootstrap_seed": BOOT_SEED,
                   "bootstrap_unit": "(instance, seed); arms are never resampled",
                   "rho_threshold": RHO_THRESHOLD, "sesoi": SESOI,
                   "gate_tol": GATE_TOL,
                   "alpha_star_source": [
                       "results/k6b-conservative.json",
                       "results/k6b-conservative-spread.json",
                       "results/p4-coord.json (k6b_rows)"],
                   "metric_status": {
                       "alpha_star": "MODEL-INTERNAL (a functional of the fitted "
                                     "posterior and nothing else)",
                       "regret": "VALIDATED (consults the noiseless oracle)",
                       "rule": "A validated metric beats a model-internal one, and the "
                               "disagreement is reported."}},
        "gate": {"tol": GATE_TOL, "rows_checked": len(rows), "worst_abs_delta": worst},
        "gate_failures": gate_failures,
        "summary": summary,
        "rows": rows}, indent=1))

    d = summary["decision"]
    p = d["primary"]
    print(f"\n{'=' * 84}")
    print(f"  tau_frac = {PRIMARY_TAU_FRAC} (primary), {p['n_arms']} arms")
    for a in p["arms"]:
        print(f"    {a:>16}  alpha*={p['mean_alpha_star'][a]:.4f}  "
              f"regret={p['mean_regret'][a]:.4f}")
    print(f"\n  Spearman rho(alpha*, regret) = {p['rho']:+.4f} "
          f"[{p['ci_lo']:+.4f}, {p['ci_hi']:+.4f}]")
    print(f"\n  VERDICT: {d['verdict']}\n  {d['wording']}")
    print(f"{'=' * 84}")
    print(f"  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
