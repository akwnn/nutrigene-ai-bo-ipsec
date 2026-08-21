"""D23-RESCORE — `doe` under rule P, with the argmax restricted to its kept factors.

    .venv/bin/python scripts/run_d23_doe_subspace.py --limit 2      # smoke
    .venv/bin/python scripts/run_d23_doe_subspace.py --gate-only    # gate, write nothing
    .venv/bin/python scripts/run_d23_doe_subspace.py                # all 50

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) **before this file existed**.

THE QUESTION
------------
D20 is this project's headline: under a posterior-mean terminal rule the regret ranking
inverts, and `doe` goes **0.0958 -> 0.1993**, first of ten to last. D23's third caveat is
that part of that collapse may be a library default rather than the design. `doe` screens
six factors down to four; its likelihood is **flat** on the two it drops, so their
lengthscales revert to the BoTorch prior mode 0.5016. Rule A never notices — it reads the
best well. Rule P takes an unconstrained argmax over all six axes and is therefore free to
walk off into two directions the data never constrained, steered by a prior.

This re-scores rule P with the argmax **restricted to the four kept factors**, the two
dropped ones held exactly where the screen held them. The difference between that and the
full-space rule P is the part of the collapse attributable to the unidentified axes.

THE REGISTERED DECISION RULE, WINNER NOT PRE-WRITTEN
-----------------------------------------------------
* subspace rule-P regret **within SESOI 0.02 of rule A's 0.0958** -> the reversal is
  substantially a prior artefact, and D20 must be relabelled *"DoE's model is unidentified
  off its screened subspace"* — a different and weaker claim.
* subspace rule-P regret **still near the full-space 0.1993** -> the prior is not the
  mechanism, the response surface is (`grid_r2` = -6.19), and D20 stands as written.
* anything between -> both mechanisms are live; the split is reported as a magnitude and
  neither wording is used alone.

The two bands are disjoint by construction: they are 0.1035 apart and each is 0.02 wide.
Nothing here can satisfy both, and the runner asserts that rather than assuming it.

WHY THE FULL-SPACE ARM IS RECOMPUTED RATHER THAN READ OFF DISK
---------------------------------------------------------------
It is read off disk **as well** — `fix1-terminal-rule.json`'s `regret_p` is the committed
column and it is the gate. But the contrast that decides this task is *paired*, and a pair
whose two halves came out of different processes is not a pair. Both halves are therefore
computed in the same call from the same fitted GP, and the full-space half is then
required to equal the committed one **exactly**. That is the only way the subspace number
is commensurable with D20's rather than merely adjacent to it.

WHAT THE LOCATOR DOES AND DOES NOT CHANGE
------------------------------------------
Identical to Fix 1 in every setting that can be held identical: the registered
20,000-point Sobol grid at seed 0 as the screen, then `constrained_argmax` at
`n_restarts=20, raw_samples=4096, seed=0`, keeping whichever candidate predicts higher.
Two things necessarily differ and both are recorded in the output `config`:

* the screen is the same 20,000 grid points with the dropped coordinates **overwritten**
  by their hold values — which is precisely the ACTIVE SUBSPACE construction Amendment B3
  already uses in `run_k6b_conservative.py`, not a new object invented here;
* the polish's own Sobol draw is 4-dimensional rather than 6-dimensional, because a
  4-dimensional search needs a 4-dimensional screen. There is no setting at which this
  can be held fixed.

D23's second caveat measured the polish beating the grid in **500/500** campaigns, so the
grid is a floor that was never needed; `regret_p_*_grid` is stored separately so that
stays checkable here too.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
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
from boec.metrics import constrained_argmax                          # noqa: E402
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import (CampaignRecord, instance_by_id,             # noqa: E402
                         regenerate, unit_bounds)
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402

ARM = "doe"
DIM, SIGMA = 6, 0.25
GRID_N, GRID_SEED = 20_000, 0
#: `boec.spread_gp`'s constants and `constrained_argmax`'s defaults, as Fix 1 used them.
N_RESTARTS, RAW_SAMPLES = 20, 4096
LOCATOR_SEED = GRID_SEED

E2_GRID = ROOT / "results" / "e2-grid.json"
FIX1 = ROOT / "results" / "fix1-terminal-rule.json"
OUT = ROOT / "results" / "d23-doe-subspace.json"

#: Exact. K1 measured `doe` at worst |delta| = 0.0 over 500 rows and Fix 1 reproduced it.
GATE_TOL = 0.0
#: The registered smallest effect of interest, and the width of both decision bands.
SESOI = 0.02
#: The two anchors the decision is read against. Committed, not recomputed here.
RULE_A_ANCHOR = 0.0958
RULE_P_FULL_ANCHOR = 0.1993
N_BOOT = 4_000
BOOT_SEED = 0


# ======================================================================================
# REGENERATION
# ======================================================================================

def regenerate_doe(instance: str, seed: int) -> CampaignRecord:
    """One committed `doe` campaign, with its `kept_factors` and `dropped_held_at`.

    Both are **recorded by the arm**, never inferred from ``X``: the 20-run screen varies
    all six factors, so every column of ``X_visited`` has nonzero variance even for the
    two the CCD never moved (`boec.replay.CampaignRecord`).
    """
    return regenerate(instance, DIM, SIGMA, seed, ARM)


# ======================================================================================
# THE TWO LOCATORS
# ======================================================================================

@dataclass(frozen=True)
class Located:
    """Where a terminal rule points, and what the screen alone would have said."""

    x: torch.Tensor
    value: float
    x_grid: torch.Tensor
    value_grid: float
    from_grid: bool
    n_starts_converged: int


def _combine(x_grid, v_grid, x_pol, v_pol, n_ok) -> Located:
    """Keep whichever candidate predicts higher. `grid_screened_argmax`'s rule."""
    if v_pol > v_grid:
        return Located(x=x_pol.double(), value=v_pol, x_grid=x_grid,
                       value_grid=v_grid, from_grid=False, n_starts_converged=n_ok)
    return Located(x=x_grid, value=v_grid, x_grid=x_grid, value_grid=v_grid,
                   from_grid=True, n_starts_converged=n_ok)


def full_argmax(predict, grid: torch.Tensor, grid_values: torch.Tensor,
                bounds: torch.Tensor) -> Located:
    """Fix 1's rule P: screen the registered grid, polish over the whole box.

    Deliberately *not* a call to `boec.metrics.grid_screened_argmax`, which returns its
    own dataclass: the two arms of this comparison must come back as the same type or a
    field-by-field write-out silently diverges between them. The rule is the same one,
    and `test_full_space_rule_p_reproduces_fix1` requires the number to be identical to
    the committed column, which is the check that matters.
    """
    values = grid_values.reshape(-1).double()
    idx = int(torch.argmax(values))
    x_pol, v_pol, n_ok = constrained_argmax(
        predict, bounds, n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES,
        seed=LOCATOR_SEED)
    return _combine(grid[idx].double().clone(), float(values[idx]), x_pol, v_pol, n_ok)


def pin(grid: torch.Tensor, held: dict[int, float]) -> torch.Tensor:
    """The registered grid with every dropped coordinate **overwritten** by its hold value.

    Amendment B3's active subspace — the construction `run_k6b_conservative.py` already
    uses to stop an arm certifying along axes its response surface never saw move. Not a
    new object invented here.
    """
    out = grid.double().clone()
    for j, v in held.items():
        out[:, int(j)] = v
    return out


def restricted_argmax(predict, pinned_grid: torch.Tensor, pinned_values: torch.Tensor,
                      kept: tuple[int, ...], held: dict[int, float],
                      bounds: torch.Tensor) -> Located:
    """The same rule, with the dropped axes pinned and the search ``len(kept)``-dimensional.

    ``pinned_values`` is passed **in**, exactly as `boec.metrics.grid_screened_argmax`
    requires, and for the same reason: `predict` here is `model.posterior(Z).mean`, which
    builds the **joint** covariance over everything handed to it. On the registered
    20,000-point grid that is 100.6 s and a 3.2 GB dense matrix whose off-diagonal is
    never used. Callers evaluate the pinned grid once through
    :func:`boec.designspace.gp_adapter`, chunked.

    The polish then runs on the ``len(kept)``-dimensional slice through a function that
    embeds back into the full box, so `predict` is only ever called on points that are
    bitwise pinned at ``held``.
    """
    kept = tuple(int(j) for j in kept)
    d = int(pinned_grid.shape[1])

    def embed(Z: torch.Tensor) -> torch.Tensor:
        """``(n, len(kept)) -> (n, d)``, dropped axes at their hold values."""
        full = torch.empty(Z.shape[0], d, dtype=torch.double)
        for j, v in held.items():
            full[:, int(j)] = v
        for col, j in enumerate(kept):
            full[:, j] = Z[:, col].double()
        return full

    def predict_sub(Z: torch.Tensor) -> torch.Tensor:
        return predict(embed(Z))

    values = pinned_values.reshape(-1).double()
    if values.numel() != pinned_grid.shape[0]:
        raise ValueError("pinned_values must carry one value per pinned_grid row; got "
                         f"{values.numel()} for {pinned_grid.shape[0]} rows")
    idx = int(torch.argmax(values))

    sub_bounds = torch.stack([bounds[0][list(kept)].double(),
                              bounds[1][list(kept)].double()])
    z_pol, v_pol, n_ok = constrained_argmax(
        predict_sub, sub_bounds, n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES,
        seed=LOCATOR_SEED)
    return _combine(pinned_grid[idx].double().clone(), float(values[idx]),
                    embed(z_pol.reshape(1, -1)).reshape(-1), v_pol, n_ok)


# ======================================================================================
# ONE CAMPAIGN, BOTH RULES, FROM ONE FITTED GP
# ======================================================================================

def score_campaign(instance: str, seed: int) -> dict:
    """Rule A, full-space rule P and subspace rule P for one committed `doe` campaign."""
    t0 = time.time()
    inst = instance_by_id(instance, DIM)
    mu_max = float(inst.optimum_value)
    bounds = unit_bounds(DIM)
    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    #: A separate oracle for scoring, so `truth` is never read off an oracle whose noise
    #: stream a regeneration is still consuming. Fix 1's convention.
    orc_t = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)

    rec = regenerate_doe(instance, seed)
    kept = tuple(int(j) for j in rec.kept_factors)
    held = {int(j): float(v) for j, v in rec.dropped_held_at.items()}

    model = build_gp(rec.X, rec.Y, rec.Yvar, bounds)

    def predict(Z: torch.Tensor, _m=model) -> torch.Tensor:
        with torch.no_grad():
            return _m.posterior(Z).mean

    # CHUNKED, BOTH OF THEM. 20k points through `model.posterior` in one call is 100.6s
    # and a 3.2 GB joint covariance whose off-diagonal is never used. The pinned screen
    # is the same size and the same trap; an earlier draft of this file evaluated it
    # unchunked and starved under memory pressure rather than failing outright.
    adapter = gp_adapter(model)
    grid_mean, _ = adapter.posterior_mean_and_sd(grid)
    pinned = pin(grid, held)
    pinned_mean, _ = adapter.posterior_mean_and_sd(pinned)

    full = full_argmax(predict, grid, grid_mean, bounds)
    sub = restricted_argmax(predict, pinned, pinned_mean, kept, held, bounds)

    with torch.no_grad():
        def truth_at(x):
            return float(orc_t.truth(x.reshape(1, -1)))
        out = {
            "instance": instance, "seed": seed, "arm": ARM, "dim": DIM, "sigma": SIGMA,
            "optimum_value": mu_max,
            "kept_factors": list(kept),
            "dropped_factors": sorted(held),
            "dropped_held_at": held,
            "regret_a": rec.regret,
            "regret_p_full": mu_max - truth_at(full.x),
            "regret_p_full_grid": mu_max - truth_at(full.x_grid),
            "regret_p_sub": mu_max - truth_at(sub.x),
            "regret_p_sub_grid": mu_max - truth_at(sub.x_grid),
            "post_mean_at_x_p_full": full.value,
            "post_mean_at_x_p_sub": sub.value,
            "from_grid_full": bool(full.from_grid),
            "from_grid_sub": bool(sub.from_grid),
            "n_starts_converged_full": int(full.n_starts_converged),
            "n_starts_converged_sub": int(sub.n_starts_converged),
            "x_p_full": [float(v) for v in full.x],
            "x_p_sub": [float(v) for v in sub.x],
            "secs": round(time.time() - t0, 2),
        }
    del model, adapter, grid_mean, pinned, pinned_mean
    gc.collect()
    return out


def _one(job: tuple[str, int]) -> dict:
    return score_campaign(*job)


# ======================================================================================
# STATISTICS  (Amendment E, restated in the Phases 2-4 registration)
# ======================================================================================

def _boot(diff: np.ndarray) -> tuple[float, float, float]:
    """4,000-resample percentile bootstrap of the paired mean, `default_rng(0)`."""
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, len(diff), size=(N_BOOT, len(diff)))
    means = diff[idx].mean(axis=1)
    return float(diff.mean()), float(np.percentile(means, 2.5)), \
        float(np.percentile(means, 97.5))


def _contrast(name: str, a: np.ndarray, b: np.ndarray) -> dict:
    """Paired ``a - b``. Bootstrap reports magnitude, Wilcoxon governs yes/no (Q20 §2)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    m, lo, hi = _boot(d)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:                                               # all-zero differences
        p = float("nan")
    return {"contrast": name, "n": int(len(d)), "mean_diff": m,
            "ci_lo": lo, "ci_hi": hi, "wilcoxon_p": p,
            "bootstrap_excludes_zero": bool(lo > 0 or hi < 0),
            "exceeds_sesoi": bool(abs(m) > SESOI)}


def _holm(contrasts: list[dict]) -> list[dict]:
    """Holm across the cells of this family. The family is these contrasts and no others."""
    order = sorted(range(len(contrasts)), key=lambda i: contrasts[i]["wilcoxon_p"])
    k = len(contrasts)
    running = 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, (k - rank) * contrasts[i]["wilcoxon_p"])
        running = max(running, adj)                                  # monotone step-down
        contrasts[i]["holm_p"] = running
        contrasts[i]["holm_sig_at_0.05"] = bool(running < 0.05)
    return contrasts


def _decide(mean_sub: float) -> dict:
    """The registered decision rule. Bands are disjoint, and that is asserted, not assumed."""
    d_a = abs(mean_sub - RULE_A_ANCHOR)
    d_p = abs(mean_sub - RULE_P_FULL_ANCHOR)
    recovers = d_a <= SESOI
    stays = d_p <= SESOI
    assert not (recovers and stays), (
        "decision bands overlap; the registered anchors are "
        f"{RULE_A_ANCHOR} and {RULE_P_FULL_ANCHOR}, {SESOI * 2} apart at most")
    if recovers:
        verdict = "PRIOR_ARTEFACT"
        wording = ("D20's reversal is substantially a prior artefact. The headline must "
                   "be relabelled \"DoE's model is unidentified off its screened "
                   "subspace\" — a different and weaker claim.")
    elif stays:
        verdict = "D20_STANDS"
        wording = ("The prior is not the mechanism; the response surface is "
                   "(grid_r2 = -6.19). D20 stands as written.")
    else:
        verdict = "BOTH_MECHANISMS_LIVE"
        wording = ("Both mechanisms are live. The split is reported as a magnitude and "
                   "neither wording is used alone.")
    #: What fraction of the full-space collapse the subspace restriction removes. The
    #: "magnitude" the third branch is required to report; defined for all three.
    collapse = RULE_P_FULL_ANCHOR - RULE_A_ANCHOR
    return {"verdict": verdict, "wording": wording,
            "mean_regret_p_subspace": mean_sub,
            "rule_a_anchor": RULE_A_ANCHOR, "distance_to_rule_a": d_a,
            "rule_p_full_anchor": RULE_P_FULL_ANCHOR, "distance_to_rule_p_full": d_p,
            "sesoi": SESOI,
            "recovers_to_rule_a": bool(recovers), "stays_at_full_space": bool(stays),
            "share_of_collapse_removed": (RULE_P_FULL_ANCHOR - mean_sub) / collapse}


def analyse(rows: list[dict]) -> dict:
    """Every registered contrast, plus the split as a magnitude."""
    rows = sorted(rows, key=lambda r: (r["instance"], r["seed"]))
    a = np.array([r["regret_a"] for r in rows])
    pf = np.array([r["regret_p_full"] for r in rows])
    ps = np.array([r["regret_p_sub"] for r in rows])

    contrasts = _holm([
        _contrast("regret_p_subspace - regret_a", ps, a),
        _contrast("regret_p_subspace - regret_p_full", ps, pf),
        _contrast("regret_p_full - regret_a  (D20's contrast, recomputed)", pf, a),
    ])

    # Per-campaign share, bootstrapped. The mean of a ratio is not the ratio of means,
    # so both are reported rather than one standing in for the other.
    denom = pf - a
    per_campaign = np.divide(pf - ps, denom, out=np.full_like(denom, np.nan),
                             where=np.abs(denom) > 1e-12)
    m, lo, hi = _boot(pf - ps)

    decision = _decide(float(ps.mean()))
    decision["collapse_removed_abs"] = {"mean": m, "ci_lo": lo, "ci_hi": hi}
    decision["share_per_campaign_median"] = float(np.nanmedian(per_campaign))
    decision["n_campaigns_with_defined_share"] = int(np.isfinite(per_campaign).sum())

    rho, rho_p = spearmanr(ps, a)
    return {
        "n": len(rows),
        "means": {"regret_a": float(a.mean()), "regret_p_full": float(pf.mean()),
                  "regret_p_subspace": float(ps.mean()),
                  "regret_p_full_grid": float(np.mean([r["regret_p_full_grid"]
                                                       for r in rows])),
                  "regret_p_subspace_grid": float(np.mean([r["regret_p_sub_grid"]
                                                           for r in rows]))},
        "medians": {"regret_a": float(np.median(a)),
                    "regret_p_full": float(np.median(pf)),
                    "regret_p_subspace": float(np.median(ps))},
        "contrasts": contrasts,
        "decision": decision,
        "spearman_subspace_vs_rule_a": {"rho": float(rho), "p": float(rho_p)},
        "polish_beat_grid": {
            "full": int(sum(not r["from_grid_full"] for r in rows)),
            "subspace": int(sum(not r["from_grid_sub"] for r in rows)),
            "of": len(rows)},
        "subspace_better_than_full_space": int((ps < pf).sum()),
        "subspace_worse_than_rule_a": int((ps > a).sum()),
    }


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


def _committed() -> tuple[dict, dict]:
    e2 = {(r["instance"], int(r["seed"])): float(r["regret"])
          for r in json.loads(E2_GRID.read_text())
          if r["arm"] == ARM and r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12}
    fix1 = {(r["instance"], int(r["seed"])): r
            for r in json.loads(FIX1.read_text())["rows"] if r["arm"] == ARM}
    return e2, fix1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--gate-only", action="store_true")
    args = ap.parse_args()

    e2, fix1 = _committed()
    keys = sorted(e2)
    if args.limit:
        keys = keys[:args.limit]

    prov = _provenance(sys.argv)
    print(f"D23-RESCORE · doe on its screened subspace · HEAD={prov['git_sha']}")
    print(f"cell d={DIM} sigma={SIGMA} · {len(keys)} (instance, seed) pairs")
    print(f"rule P: {GRID_N}-pt Sobol grid seed {GRID_SEED}, polished at "
          f"n_restarts={N_RESTARTS} raw_samples={RAW_SAMPLES} seed={LOCATOR_SEED}")
    print(f"gate: committed rule-A regret must reproduce at |delta| = {GATE_TOL:g} "
          f"EXACTLY (results/e2-grid.json)")
    print(f"check: full-space rule P must reproduce results/fix1-terminal-rule.json\n",
          flush=True)

    rows: list[dict] = []
    gate_failures: list[dict] = []
    fix1_deltas: list[dict] = []
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for k, r in enumerate(pool.map(_one, keys), 1):
            key = (r["instance"], r["seed"])
            delta = abs(r["regret_a"] - e2[key])
            r["regret_a_committed"] = e2[key]
            r["gate_abs_delta"] = delta
            if delta > GATE_TOL:
                gate_failures.append({"instance": key[0], "seed": key[1],
                                      "regret_a": r["regret_a"],
                                      "regret_a_committed": e2[key],
                                      "gate_abs_delta": delta,
                                      "gate_source": "results/e2-grid.json"})
                print(f"  !! GATE {key} |delta|={delta:.3e}", flush=True)

            # NOT the registered gate. A separate, reported measurement: it says whether
            # the full-space half of this pair is Fix 1's number or merely close to it.
            ref = fix1.get(key)
            if ref is not None:
                r["regret_p_full_committed"] = ref["regret_p"]
                r["fix1_abs_delta"] = abs(r["regret_p_full"] - ref["regret_p"])
                fix1_deltas.append({"instance": key[0], "seed": key[1],
                                    "abs_delta": r["fix1_abs_delta"]})
            rows.append(r)
            el = time.time() - t0
            print(f"  [{k:3d}/{len(keys)}] {key[0]} seed={key[1]}  "
                  f"A={r['regret_a']:.4f} P_full={r['regret_p_full']:.4f} "
                  f"P_sub={r['regret_p_sub']:.4f}  kept={r['kept_factors']}  "
                  f"{el/60:4.1f} min", flush=True)

    worst = max((r["gate_abs_delta"] for r in rows), default=0.0)
    worst_fix1 = max((d["abs_delta"] for d in fix1_deltas), default=float("nan"))
    print(f"\n  gate (rule A vs e2-grid.json): {len(rows)} rows, worst |delta| = "
          f"{worst:.3e}, {len(gate_failures)} failures")
    print(f"  check (rule P full vs fix1-terminal-rule.json): worst |delta| = "
          f"{worst_fix1:.3e}")

    if gate_failures:
        print("\n*** STOP. A regenerated `doe` campaign is not the committed campaign. "
              "Reported, not worked around. ***")
        raise SystemExit(1)
    if args.gate_only:
        return

    summary = analyse(rows)
    OUT.write_text(json.dumps({
        "provenance": prov,
        "config": {
            "arm": ARM, "dim": DIM, "sigma": SIGMA, "grid_n": GRID_N,
            "grid_seed": GRID_SEED, "n_restarts": N_RESTARTS,
            "raw_samples": RAW_SAMPLES, "locator_seed": LOCATOR_SEED,
            "gate_tol": GATE_TOL, "sesoi": SESOI, "n_boot": N_BOOT,
            "bootstrap_seed": BOOT_SEED,
            "rule_a": "optimum_value - truth(argmax observed Y)",
            "rule_p_full": ("optimum_value - truth(argmax posterior mean over the whole "
                            f"box), screened on the {GRID_N}-pt Sobol grid at seed "
                            f"{GRID_SEED} and polished with constrained_argmax("
                            f"n_restarts={N_RESTARTS}, raw_samples={RAW_SAMPLES}, "
                            f"seed={LOCATOR_SEED})"),
            "rule_p_subspace": ("the same rule with the argmax restricted to the arm's "
                                "kept_factors, dropped factors pinned bitwise at "
                                "dropped_held_at; the screen is the same 20,000 grid "
                                "points with the dropped coordinates overwritten "
                                "(Amendment B3's active subspace), and the polish's own "
                                "Sobol draw is len(kept)-dimensional, which is the one "
                                "setting that cannot be held equal to the full-space arm"),
            "gate_source": "results/e2-grid.json · arm doe · d=6 sigma=0.25",
            "fix1_check_source": "results/fix1-terminal-rule.json · arm doe · regret_p"},
        "gate": {"tol": GATE_TOL, "rows_checked": len(rows), "worst_abs_delta": worst,
                 "failures": gate_failures},
        "fix1_reproduction_check": {
            "note": ("NOT the registered gate. Measured and reported: whether the "
                     "full-space half of each pair is Fix 1's committed number."),
            "rows_checked": len(fix1_deltas), "worst_abs_delta": worst_fix1,
            "n_exact": int(sum(d["abs_delta"] == 0.0 for d in fix1_deltas))},
        "gate_failures": gate_failures,
        "summary": summary,
        "rows": rows}, indent=1))

    d = summary["decision"]
    print(f"\n{'=' * 84}")
    print(f"  rule A          {summary['means']['regret_a']:.4f}")
    print(f"  rule P full     {summary['means']['regret_p_full']:.4f}")
    print(f"  rule P subspace {summary['means']['regret_p_subspace']:.4f}")
    print(f"  distance to rule A anchor {RULE_A_ANCHOR}: "
          f"{d['distance_to_rule_a']:.4f}  (SESOI {SESOI})")
    print(f"  distance to full-space anchor {RULE_P_FULL_ANCHOR}: "
          f"{d['distance_to_rule_p_full']:.4f}")
    print(f"  share of the collapse removed: {d['share_of_collapse_removed']:.3f}")
    print(f"\n  VERDICT: {d['verdict']}\n  {d['wording']}")
    print(f"{'=' * 84}")
    print(f"  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
