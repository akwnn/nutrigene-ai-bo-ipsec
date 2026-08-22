"""Version C Form 1 -- the re-score. **Zero new wells.**

    .venv/bin/python scripts/run_versionc_form1.py --sigma 0.10 --limit 2   # smoke
    .venv/bin/python scripts/run_versionc_form1.py --sigma 0.10             # all 50 keys

------------------------------------------------------------------------------
WHY THIS IS A RE-SCORE AND NOT A CAMPAIGN
------------------------------------------------------------------------------

C0 returned **IDENTIFICATION_ARTEFACT** (FINDINGS §32): the σ=0.10 regret deficit was rule
A's winner's curse, not a search failure, so **§2's trust region was not built**. C3.3b
predicts **K-C7 fires**, so the detector does not gate. With ``m = 0`` and no detector,
§5's arm table collapses:

    versionc == versionc_form1 == versionc_nodetect     one arm
    versionc_fixed_m                                    moot -- needs §2
    versionc_random  ==  versionb_random                already committed

and §1's three changes are **scoring and reporting only** -- §1.4 keeps plate 1, the LSE
criterion and the predictive straddle unchanged. So **Version C Form 1's campaign is
Version B's campaign**, and Version C is:

    rule P as the terminal rule | split-sample CE | components + five columns + non-vacuity

**The attribution this buys is the cleanest available.** The arms are campaign-identical,
so any difference from Version B is attributable to the three scoring changes and to
nothing else -- *provided* every shared column reproduces at ``|delta| = 0``. That proviso
is the point of the gate below, and it is why the base scoring is not reimplemented here.

------------------------------------------------------------------------------
THE BASE SCORING IS `run_p3_cells`'s OWN FUNCTION, CALLED
------------------------------------------------------------------------------

``score_k6_dual_tau`` and ``score_k6b`` are **imported and called**, not copied. A second
implementation of the K6 row would have to be argued into agreement; a call to the first
one agrees **by construction**. D12's lesson is the same one from the other direction: a
gate that compares one fresh run to another can only report that the code agrees with
itself. Here the committed file is the reference and the same function produces both sides.

------------------------------------------------------------------------------
THE ONE PLACE THE ARITHMETIC HAD TO CHANGE, AND WHY IT IS SAFE
------------------------------------------------------------------------------

The cross-fit needs **two** blocks of 512 joint draws. ``joint_draws`` builds a fresh
generator per call, so calling it twice returns the identical block -- two copies of one
draw, which as a cross-fit would silently report the circular number as if it were held
out. And ``randn(n, 1024)[:, :512]`` is **not** ``randn(n, 512)`` at the same seed, because
torch fills in memory order, so drawing both at once would move every committed column.

``boec.versionc.split_joint_draws`` draws both halves sequentially from one generator, and
``tests/test_versionc.py`` asserts its **first half is bit-identical to
``joint_draws(model, X, seed=seed)``**. That is the load-bearing property of this file.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import math
import os
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import (component_report, gp_adapter,            # noqa: E402
                              grid_neighbours, predictive_probability_map,
                              probability_map, tau_max)
from boec.metrics import grid_screened_argmax                          # noqa: E402
from boec.norms import sobol_grid                                      # noqa: E402
from boec.replay import instance_by_id, unit_bounds                    # noqa: E402
from boec.surrogate import build_gp                                    # noqa: E402
from boec.torch_oracle import BiphasicOracle                           # noqa: E402
from boec.versionc import conservative_columns, split_joint_draws      # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


#: Imported and CALLED, never copied. See the module docstring.
_P3 = _load("_run_p3_cells", ROOT / "scripts" / "run_p3_cells.py")

DIM, BUDGET = 6, 48
GRID_N, SUBSET_N, GRID_SEED = 20_000, 2_000, 0
N_DRAWS_HALF = 512
ALPHAS = (0.50, 0.80, 0.95)
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
N_RESTARTS, RAW_SAMPLES = 20, 4096

#: The Version C arm that is actually run. The other two labels are the same campaign.
COLLAPSED_INTO = "versionc_form1"

#: Every §5 label, mapped to the campaign that actually exists. Recorded so a reader of
#: the results file can see that the collapse was reasoned rather than an omission.
ARM_ALIASES = {
    "versionc": "versionc_form1",
    "versionc_nodetect": "versionc_form1",
    "versionc_form1": "versionc_form1",
    "versionc_random": "versionb_random",
}

MOOT_ARMS = {
    "versionc_fixed_m": ("splits 4 trust + 4 boundary, and section 2's trust region was "
                         "never built -- C0 returned IDENTIFICATION_ARTEFACT"),
}

#: `plate1_only` IS `lhs` at 48 wells. Including it makes `lhs` a second arm; this was
#: wrong in the first cut of the Part IV headline and had to be redone.
NEVER_RANK_SEPARATELY = {"plate1_only": "lhs"}

#: Version C's campaign is Version B's, so `versionb` IS the arm re-scored. The
#: comparators come along so the map ranking is computable in one file.
ARMS = ("doe", "qlogei", "qlognei", "qlogei-add", "qlogei-addonly", "lhs", "sobol",
        "random", "plate1_only", "versionb", "versionb_random", "versionb_predictive")

#: Exact. A re-score that changes a number it was not supposed to change is a bug.
GATE_TOL = 0.0

#: FULL WIDTH, not a sample. Every committed K6 field.
GATED_COLUMNS = (
    "regret", "sup_err", "grid_r2", "tau", "tau_max", "true_frac_above_tau",
    "vol_pred", "vol_latent", "empty_pred", "empty_latent", "iou_pred", "iou_latent",
    "fi_pred", "fi_latent", "brier_pred", "auc_pred", "brier_latent", "auc_latent",
    "box_vol_pred", "n_active",
)

#: What Version C adds. Disjoint from GATED_COLUMNS by construction -- a new column that
#: shadowed a committed one would make the gate compare the new number against itself.
ADDED_COLUMNS = (
    "regret_p", "regret_p_grid", "improvement_a_minus_p",
    "non_vacuous_pred", "non_vacuous_latent", "ce_non_vacuous_0.95",
    "ce_split_contain_0.5", "ce_split_contain_0.8", "ce_split_contain_0.95",
    "ce_selection_bias_0.5", "ce_selection_bias_0.8", "ce_selection_bias_0.95",
    "ce_fi_0.5", "ce_fi_0.8", "ce_fi_0.95",
    "n_components_pred", "largest_component_vol", "component_box_vol_sum",
    "box_vol_all_components",
)

#: Registered BEFORE the run. If components help everywhere equally, something is wrong.
COMPONENT_PREDICTION = {
    "largest": "hartmann6",
    "near_zero": "hill",
    "why": ("hartmann6 is multimodal with disconnected superlevel sets, so a single "
            "inscribed box is bounded by the largest component; hill is unimodal and has "
            "one component, so the decomposition has nothing to recover"),
}

OUT = ROOT / "results" / "versionc-form1"


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float, bool)) else None


def gate_row(row: dict, ref: dict | None) -> list[dict]:
    """Every shared column, compared at ``|delta| = 0``. ``nan`` matches ``nan``.

    **nan matching is not a loosened tolerance.** 54-69% of predictive regions are empty at
    some cells, where `fi` and `iou` are `nan` by design -- `nan != nan` would fire the
    gate on the most common row in the study rather than on a defect.
    """
    if ref is None:
        return []
    out = []
    for col in GATED_COLUMNS:
        if col not in row or col not in ref:
            continue
        a, b = _num(row[col]), _num(ref[col])
        if a is None or b is None:
            if row[col] != ref[col]:
                out.append({"column": col, "got": row[col], "expected": ref[col]})
            continue
        if math.isnan(a) and math.isnan(b):
            continue
        if math.isnan(a) != math.isnan(b) or abs(a - b) > GATE_TOL:
            out.append({"column": col, "got": a, "expected": b,
                        "abs_delta": (float("nan") if math.isnan(a) or math.isnan(b)
                                      else abs(a - b))})
    return out


def committed_index(path: Path) -> dict[tuple, dict]:
    """``(instance, seed, arm, gamma, tau_frac) -> committed row``."""
    payload = json.loads(path.read_text())
    rows = payload["rows"] if isinstance(payload, dict) else payload
    return {(r["instance"], int(r["seed"]), r["arm"],
             round(float(r["gamma"]), 10), round(float(r["tau_frac"]), 10)): r
            for r in rows if "gamma" in r and "tau_frac" in r}


def score_one(inst_id: str, seed: int, sigma: float, arms=ARMS,
              grid=None, X_sub=None, neighbours=None) -> list[dict]:
    """Every arm for one ``(instance, seed)``: P3's K6 rows plus Version C's additions."""
    inst = instance_by_id(inst_id, DIM)
    mu_max = float(inst.optimum_value)
    bounds = unit_bounds(DIM)
    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED) if grid is None else grid
    X_sub = sobol_grid(DIM, SUBSET_N, seed=GRID_SEED) if X_sub is None else X_sub
    orc_t = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    with torch.no_grad():
        truth = orc_t.truth(grid).reshape(-1).double()
    active = torch.ones(DIM, dtype=torch.bool)

    rows: list[dict] = []
    for arm in arms:
        t0 = time.time()
        rec = _P3.regenerate_arm(inst_id, DIM, sigma, seed, arm)
        orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)

        # --- the committed K6 rows, from P3's OWN function -------------------------
        base_rows, _sens = _P3.score_k6_dual_tau(rec, orc, grid, truth, active)

        # --- rule P: one locator, one setting, every arm ---------------------------
        model = build_gp(rec.X, rec.Y, rec.Yvar, bounds)

        def predict(Z: torch.Tensor, _m=model) -> torch.Tensor:
            with torch.no_grad():
                return _m.posterior(Z).mean

        grid_mean, grid_sd = gp_adapter(model).posterior_mean_and_sd(grid)
        r = grid_screened_argmax(predict, grid, grid_mean, bounds,
                                 n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES,
                                 seed=GRID_SEED)
        with torch.no_grad():
            regret_p = float(mu_max - orc_t.truth(r.x.reshape(1, -1)))
            regret_p_grid = float(mu_max - orc_t.truth(r.x_grid.reshape(1, -1)))

        # --- the cross-fit halves, first bit-identical to the committed draw --------
        with torch.no_grad():
            truth_sub = orc_t.truth(X_sub).reshape(-1).double()
        sel, val = split_joint_draws(model, X_sub, n_draws=N_DRAWS_HALF, seed=seed)

        sigma_pred = ((sigma * grid_mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

        for row in base_rows:
            gamma, tf = float(row["gamma"]), float(row["tau_frac"])
            tau = float(row["tau"])
            theta = tf * mu_max

            row["regret_p"] = regret_p
            row["regret_p_grid"] = regret_p_grid
            row["improvement_a_minus_p"] = float(rec.regret) - regret_p

            # Non-vacuity, registered as a metric so D21's effect has a home instead of
            # surfacing post-hoc a third time.
            row["non_vacuous_pred"] = not bool(row["empty_pred"])
            row["non_vacuous_latent"] = not bool(row["empty_latent"])

            # Split-sample CE, at this row's own theta.
            cc = conservative_columns(sel, val, truth_sub, theta, alphas=ALPHAS)
            for k, v in cc.items():
                if k not in ("alpha_star", "vorobev_deviation", "true_frac_above_tau"):
                    row[f"{k}" if k.startswith("ce_") else f"ce_{k}"] = v
            row["ce_non_vacuous_0.95"] = not bool(cc["ce_empty_0.95"])

            # Connected components of D_gamma, with the single-box number alongside.
            p_pred = predictive_probability_map(_Grid(grid_mean, grid_sd), grid, tau,
                                                sigma_pred)
            d_gamma = p_pred >= gamma
            comps = component_report(d_gamma, grid, truth, tau, neighbours=neighbours,
                                     active=active, seed_score=p_pred)
            row["n_components_pred"] = comps[0]["n_components"] if comps else 0
            row["largest_component_vol"] = comps[0]["vol"] if comps else 0.0
            row["component_box_vol_sum"] = sum(c["box_vol"] for c in comps)
            row["box_vol_all_components"] = (comps[0]["box_vol_all_components"]
                                             if comps else 0.0)
            row["components"] = [
                {k: c[k] for k in ("component", "n_points", "vol", "box_vol", "fi",
                                   "empirical_containment", "total_error_vol")}
                for c in comps]
            row["arm_alias_of"] = ARM_ALIASES.get(arm)
            row["never_rank_separately"] = NEVER_RANK_SEPARATELY.get(arm)
            row["secs"] = round(time.time() - t0, 2)

        rows.extend(base_rows)
        del model, grid_mean, grid_sd, sel, val
        gc.collect()
    return rows


class _Grid:
    """The grid mean/sd, already paid for. Only ever called with ``grid``."""

    def __init__(self, mean, sd):
        self._m, self._s = mean, sd

    def posterior_mean_and_sd(self, Z):
        return self._m, self._s


# --- provenance and partial discipline --------------------------------------------------

def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch, gpytorch, numpy, scipy                           # noqa: E401
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def _partial_path(final: Path) -> Path:
    return final.with_suffix(final.suffix + ".partial")


def write_partial(final: Path, rows, keys_present: int, keys_expected: int, argv,
                  cfg: dict, gate_failures=None) -> Path:
    """Write to ``<name>.partial``. **Never** to the registered path."""
    complete = keys_present == keys_expected
    path = _partial_path(final)
    path.write_text(json.dumps({
        "status": "complete" if complete else "partial", "complete": complete,
        "keys_present": keys_present, "keys_expected": keys_expected,
        "provenance": _provenance(argv), "config": cfg,
        "collapsed_into": COLLAPSED_INTO, "arm_aliases": ARM_ALIASES,
        "moot_arms": MOOT_ARMS, "never_rank_separately": NEVER_RANK_SEPARATELY,
        "component_prediction": COMPONENT_PREDICTION,
        "gate": {"tol": GATE_TOL, "columns": list(GATED_COLUMNS),
                 "failures": gate_failures or []},
        "rows": rows}, indent=1))
    return path


def promote(final: Path) -> dict:
    """Move a **complete** partial onto the registered path, then re-read it."""
    path = _partial_path(final)
    payload = json.loads(path.read_text())
    if not payload.get("complete"):
        raise ValueError(f"refusing to promote an incomplete partial: "
                         f"{payload.get('keys_present')} of "
                         f"{payload.get('keys_expected')} keys")
    final.write_text(path.read_text())
    republished = json.loads(final.read_text())
    if republished != payload:
        raise ValueError("promoted file does not re-read as what was written")
    path.unlink()
    return republished


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigma", type=float, default=0.10)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--arms", type=str, default=None)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    sigma = args.sigma
    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    final = Path(args.out) if args.out else Path(f"{OUT}-s{int(sigma*100):03d}.json")

    ref_path = (ROOT / "results" / "p3-k6-d6-s010.json" if abs(sigma - 0.10) < 1e-9
                else ROOT / "results" / "p2-versionb-gamma.json")
    committed = committed_index(ref_path)
    keys = sorted({(k[0], k[1]) for k in committed})
    if args.limit:
        keys = keys[:args.limit]

    cfg = {"dim": DIM, "sigma": sigma, "budget": BUDGET, "arms": list(arms),
           "gammas": list(GAMMAS), "tau_fracs": list(TAU_FRACS), "alphas": list(ALPHAS),
           "grid_n": GRID_N, "subset_n": SUBSET_N, "grid_seed": GRID_SEED,
           "n_draws_half": N_DRAWS_HALF, "gate_reference": ref_path.name,
           "gate_tol": GATE_TOL, "added_columns": list(ADDED_COLUMNS)}

    print(f"Version C Form 1 re-score · sigma={sigma} · ZERO NEW WELLS")
    print(f"{len(arms)} arms x {len(keys)} keys · gate {ref_path.name} "
          f"at |delta| = {GATE_TOL} over {len(GATED_COLUMNS)} columns\n")

    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(DIM, SUBSET_N, seed=GRID_SEED)
    print("building the grid neighbour graph once ...", flush=True)
    neighbours = grid_neighbours(grid)

    rows, failures = [], []
    for n, (inst_id, seed) in enumerate(keys, start=1):
        t0 = time.time()
        got = score_one(inst_id, seed, sigma, arms, grid=grid, X_sub=X_sub,
                        neighbours=neighbours)
        for row in got:
            key = (row["instance"], int(row["seed"]), row["arm"],
                   round(float(row["gamma"]), 10), round(float(row["tau_frac"]), 10))
            bad = gate_row(row, committed.get(key))
            if bad:
                failures.append({"key": list(key), "failures": bad})
        if failures:
            print(f"\nGATE FAILED on {len(failures)} rows, first: {failures[0]}")
            raise SystemExit(1)
        rows.extend(got)
        print(f"[{n:3d}/{len(keys)}] {inst_id} seed={seed} "
              f"comps {min(r['n_components_pred'] for r in got)}"
              f"..{max(r['n_components_pred'] for r in got)} "
              f"({time.time()-t0:.1f}s)", flush=True)
        write_partial(final, rows, n, len(keys), sys.argv, cfg, failures)

    payload = promote(final)
    print(f"\npromoted {final.name} · {len(payload['rows'])} rows · gate clean")


if __name__ == "__main__":
    main()
