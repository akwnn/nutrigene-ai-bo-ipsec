"""P1 — gate the kernel arms, then re-score the 2,800 committed rows that rest on them.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) under "PHASES 2-4
PRE-REGISTRATION", before this file existed. Amendment A1 / Q30.

------------------------------------------------------------------------------
WHAT WAS BROKEN
------------------------------------------------------------------------------
`scripts/run_k6_designspace.py:161-162` builds its `committed` dict from
`committed_rows()`, whose default path is `results/e2-grid.json`. That file carries
seven arms and **no kernel arms**, so line 181's `if ref is not None` skipped 100
campaigns without a word, and `run_k6b_conservative.py:135-136` skipped the same 100
(COVERAGE-MATRIX §3.6). Both files report `gate_failures: 0`. Neither ran the gate.

`results/q30-additive.json` — the comparator Amendment A1 named — had never existed.
Phase 2's DECISION 1 re-runs `scripts/run_q30_additive.py` unmodified to create it.

------------------------------------------------------------------------------
WHY THIS IS A GATE AND NOT A CIRCLE (D12)
------------------------------------------------------------------------------
`run_q30_additive.py` is the original campaign runner: it drives `Campaign` directly.
`src/boec/replay.py` is an independent reimplementation written months later for the
K-series. The two share `Campaign` but not the surrounding scoring path, and neither
reads the other. Their agreement at |Δ| = 0 is the same structure that makes
`e2-grid.json` a valid gate target — it is not one run compared with itself.

Gating the kernel arms against `k6-designspace.json` would be circular, which is why
the registration rejects it and why this file exists at all.

------------------------------------------------------------------------------
THE CONTROL ARMS, WHICH THE REGISTRATION DID NOT ASK FOR AND THE VERDICT NEEDS
------------------------------------------------------------------------------
The registered kill condition is severe: **any Δ ≠ 0 withdraws 2,800 committed rows.**
K6b's scoring is inline in `run_k6b_conservative.main()` and cannot be imported, so it
is re-expressed here. A defect in that re-expression would manufacture a false
WITHDRAWN — the most damaging outcome available, and one no amount of re-running would
distinguish from a real one.

So the same re-score path is applied to arms that are **already gated against
`e2-grid.json`**: every `doe` campaign (regeneration costs 0.1 s and it exercises the
Amendment B3 active-subspace branch) and a `qlogei` subsample (which takes the same
`kept_factors is None` branch the kernel arms take). If the controls reproduce their
committed rows at |Δ| = 0, the harness is sound and any kernel-arm delta is about the
kernel arms. If a control also fails, the finding is about this file, and it says so.

The 5-campaign subsample mirrors `run_q30_additive.check_fidelity`'s own
`FIDELITY_SUBSAMPLE = 5`; `qlogei` regeneration is 62 s/campaign at this cell.

------------------------------------------------------------------------------
FIDELITY OF THE RE-SCORE
------------------------------------------------------------------------------
Verified before this ran: between `147f1c0` (which produced `k6-designspace.json`) and
HEAD, `designspace.py`, `norms.py`, `surrogate.py`, `campaign.py`, `torch_oracle.py`
and `oracles.py` are untouched; `run_k6_designspace.py` gained only `--arms`/`--out`;
and `replay.py`'s two commits add the `SPREAD_ARMS` branch and `dropped_held_at`,
leaving the `arm in KERNEL_ARMS` path byte-identical. `k6b-conservative.json` was
produced at `b3de1d2`, since which none of these files changed at all. A re-score at
HEAD is therefore a comparison of the numbers, not of two code versions.

K6 and K6b are re-scored in **separate passes**, each regenerating its own campaign,
because that is the order the original runs used: K6 goes `regenerate` → `build_gp`
inside `score_campaign`, K6b goes `regenerate` → `build_gp` → `joint_draws`. Sharing
one regeneration across both would put `build_gp` at a different point in the global
RNG stream than the committed run did. The duplicated regeneration costs ~20 min and
removes a whole class of doubt about a verdict that withdraws 2,800 rows.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import instance_by_id, regenerate, unit_bounds      # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402
from boec.vorobev import (alpha_star, conservative_estimate,          # noqa: E402
                          containment_probability, empirical_containment,
                          excursion_probability, vorobev_deviation,
                          vorobev_expectation)

# The scoring code under test is IMPORTED from the committed runners, never copied,
# so a re-score cannot silently drift from the run that produced the committed rows.
from run_k6_designspace import score_campaign                         # noqa: E402
from run_k6_designspace import GAMMAS, GRID_N, GRID_SEED, TAU_FRACS   # noqa: E402
from run_k6b_conservative import ALPHAS, N_DRAWS, SUBSET_N, joint_draws  # noqa: E402
from run_k6b_conservative import TAU_FRACS as K6B_TAU_FRACS           # noqa: E402

Q30 = Path("results/q30-additive.json")
K6 = Path("results/k6-designspace.json")
K6B = Path("results/k6b-conservative.json")
OUT = Path("results/p1-kernel-gate.json")

#: The arms A1 added and never gated.
KERNEL_ARMS = ("qlogei-add", "qlogei-addonly")
#: Gated against `e2-grid.json` in both committed runs, so they prove the harness.
CONTROL_ARMS = ("doe", "qlogei")

#: The cell K6/K6b were run at. `q30-additive.json` also carries sigma 0.10, which has
#: no design-space rows anywhere and is gate-only.
DIM = 6
PRIMARY_SIGMA = 0.25

K6_KEYS = ("instance", "dim", "sigma", "seed", "arm", "gamma", "tau_frac")
K6B_KEYS = ("instance", "dim", "sigma", "seed", "arm", "tau_frac")
Q30_KEYS = ("instance", "dim", "sigma", "seed", "arm")

#: The registration's own number. Asserted, never inferred from the files themselves.
REGISTERED_K6_ROWS = 2400
REGISTERED_K6B_ROWS = 400


# --------------------------------------------------------------------------- exactness


def abs_delta(a, b) -> float:
    """|a − b|, with the two cases a plain subtraction gets wrong.

    NaN is a *value* in these files — `fi_pred` is NaN in 1,398 committed kernel rows
    because the certified set is empty there — so NaN reproducing as NaN is agreement,
    not a failure. NaN against a number is total disagreement, hence `inf` rather than
    NaN, which would compare false against every threshold and pass the gate.

    Booleans are compared as booleans. `empty_pred` flipping True→False is a different
    region, not a difference of 1.0.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return 0.0 if a is b or a == b else math.inf
    if a is None or b is None:
        return math.inf
    fa, fb = float(a), float(b)
    na, nb = math.isnan(fa), math.isnan(fb)
    if na and nb:
        return 0.0
    if na or nb:
        return math.inf
    return abs(fa - fb)


def metric_columns(row: dict, keys: tuple[str, ...]) -> tuple[str, ...]:
    """Every column that is not part of the key. Nothing is hand-picked.

    A re-score that compares a chosen subset of metrics is how a moved row passes a
    gate, so the set is derived from the committed row itself and cannot go stale when
    a column is added.
    """
    return tuple(k for k in row if k not in keys)


def compare_row(committed: dict, rescored: dict, keys: tuple[str, ...]) -> list[dict]:
    """Per-metric failures for one row. Empty list means |Δ| = 0 on every column."""
    fails = []
    for col in metric_columns(committed, keys):
        d = abs_delta(committed[col], rescored.get(col, None))
        if d != 0.0:
            fails.append({**{k: committed[k] for k in keys}, "metric": col,
                          "committed": _jsonable(committed[col]),
                          "rescored": _jsonable(rescored.get(col, None)),
                          "abs_delta": d})
    return fails


def _jsonable(v):
    if isinstance(v, float) and not math.isfinite(v):
        return str(v)
    return v


def _sanitize(o):
    """Recursively make a payload writable under ``allow_nan=False``.

    `abs_delta` is `inf` whenever a NaN column failed to reproduce as NaN, and
    `json.dumps` raises on non-finite floats rather than the `default=` hook. Losing
    a four-hour run at the write step, after the verdict is known, is avoidable.
    """
    if isinstance(o, dict):
        return {k: _sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sanitize(v) for v in o]
    return _jsonable(o)


# ------------------------------------------------------------------------- indexing


def index_rows(rows: list[dict], keys: tuple[str, ...]) -> dict[tuple, dict]:
    """Key → row. A duplicate key raises: one row silently shadowing another is how
    a re-score compares 2,799 rows and reports 2,800."""
    out: dict[tuple, dict] = {}
    for r in rows:
        k = tuple(r[c] for c in keys)
        if k in out:
            raise ValueError(f"duplicate key {k} in the committed rows")
        out[k] = r
    return out


def committed_index(path: Path, keys: tuple[str, ...],
                    arms: tuple[str, ...] = KERNEL_ARMS) -> dict[tuple, dict]:
    """The committed kernel-arm rows of a K6/K6b file, exactly as stored."""
    rows = json.loads(Path(path).read_text())["rows"]
    return index_rows([r for r in rows if r["arm"] in arms], keys)


def gate_regret(comparator: dict[tuple, dict], *, instance: str, dim: int,
                sigma: float, seed: int, arm: str, regenerated: float) -> dict:
    """Gate one regenerated regret against its committed comparator.

    **Raises** when the comparator has no such row. `committed.get(...)` returning
    `None` and being treated as a pass is the §3.6 defect this whole file exists to
    close; a gate with nothing to gate against is a missing gate, not a passing one.
    """
    key = (instance, dim, sigma, seed, arm)
    if key not in comparator:
        raise KeyError(
            f"no comparator row for {key} — the gate cannot be skipped silently")
    ref = float(comparator[key]["regret"])
    d = abs_delta(ref, regenerated)
    return {"instance": instance, "dim": dim, "sigma": sigma, "seed": seed, "arm": arm,
            "committed": ref, "regenerated": float(regenerated),
            "abs_delta": d, "passed": d == 0.0}


# -------------------------------------------------------------------------- verdict


def assert_full_coverage(*, rescored_k6: int, rescored_k6b: int) -> None:
    """A short re-score is the §3.6 silence, not a pass."""
    if rescored_k6 != REGISTERED_K6_ROWS or rescored_k6b != REGISTERED_K6B_ROWS:
        raise ValueError(
            f"coverage: expected {REGISTERED_K6_ROWS} K6 and {REGISTERED_K6B_ROWS} "
            f"K6b kernel-arm rows (2800 total), re-scored "
            f"{rescored_k6} and {rescored_k6b}")


def verdict(gate_failures: list[dict], rescore_failures: list[dict]) -> str:
    """The registered kill condition. |Δ| = 0 everywhere, or the rows are withdrawn."""
    return "WITHDRAWN" if (gate_failures or rescore_failures) else "VALIDATED"


def provenance() -> dict:
    """Modelled on `results/q52-budget-to-target.json`, as registered."""
    import botorch
    import gpytorch
    import scipy
    sha = subprocess.run(["git", "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True).stdout.strip())
    return {"git_sha": sha, "git_dirty": dirty,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"),
            "argv": sys.argv, "python": platform.python_version(),
            "torch": torch.__version__, "botorch": botorch.__version__,
            "gpytorch": gpytorch.__version__, "numpy": np.__version__,
            "scipy": scipy.__version__,
            "torch_num_threads": torch.get_num_threads()}


# ------------------------------------------------------------------------ K6b scoring


def score_campaign_k6b(rec, orc, X_sub, mu_max, dim) -> list[dict]:
    """K6b's per-campaign rows.

    Re-expressed from `run_k6b_conservative.main()`, which builds them inline and
    exposes no function to import. Every constant is imported from that module rather
    than retyped, and the control arms above exist precisely because this block is a
    re-expression: if it has drifted, `doe` and `qlogei` fail their own gate first.
    """
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(dim))

    # AMENDMENT B3: an arm that never varied a factor may not certify a range for it.
    if rec.kept_factors is not None and rec.dropped_held_at:
        X_eval = X_sub.clone()
        for j, v in rec.dropped_held_at.items():
            X_eval[:, j] = v
    else:
        X_eval = X_sub
    with torch.no_grad():
        truth_eval = orc.truth(X_eval).reshape(-1).double()
    draws = joint_draws(model, X_eval, seed=rec.seed)

    rows = []
    for tf in K6B_TAU_FRACS:
        theta = tf * mu_max
        p = excursion_probability(draws, theta)
        q = vorobev_expectation(p, draws, theta)
        true_set = truth_eval >= theta
        inter = int((q & true_set).sum())
        union = int((q | true_set).sum())
        row = {"instance": rec.instance, "dim": dim, "sigma": rec.sigma,
               "seed": rec.seed, "arm": rec.arm, "regret": rec.regret,
               "tau_frac": tf, "theta": theta,
               "true_frac_above": float(true_set.double().mean()),
               "n_active": (dim if rec.kept_factors is None
                            else len(rec.kept_factors)),
               "alpha_star": alpha_star(draws, theta),
               "vorobev_deviation": vorobev_deviation(draws, theta),
               "vorobev_expectation_vol": float(q.double().mean()),
               "iou_vorobev_expectation": (inter / union) if union else float("nan"),
               "max_p": float(p.max())}
        for a in ALPHAS:
            ce = conservative_estimate(draws, theta, a)
            n_ce = int(ce.sum())
            row[f"ce_vol_{a}"] = n_ce / ce.numel()
            row[f"ce_empty_{a}"] = n_ce == 0
            row[f"ce_false_in_{a}"] = (
                float((truth_eval[ce] < theta).double().mean()) if n_ce
                else float("nan"))
            row[f"ce_contain_{a}"] = (containment_probability(draws, ce, theta)
                                      if n_ce else float("nan"))
            emp = empirical_containment(ce, truth_eval, theta)
            row[f"ce_empirical_{a}"] = float("nan") if emp is None else float(emp)
        rows.append(row)
    del model, draws
    gc.collect()
    return rows


# ------------------------------------------------------------------------------ run


def _pairs(index: dict[tuple, dict]) -> list[tuple[str, int]]:
    """The (instance, seed) pairs at the primary cell, in the committed order."""
    return sorted({(k[0], k[3]) for k in index})


def _write(payload: dict) -> None:
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(_sanitize(payload), indent=1, allow_nan=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="(instance, seed) pairs to run; default all 50. Smoke tests "
                         "only — a limited run cannot pass assert_full_coverage.")
    ap.add_argument("--qlogei-control", type=int, default=5,
                    help="qLogEI control campaigns; 0 disables. Mirrors "
                         "run_q30_additive.FIDELITY_SUBSAMPLE.")
    args = ap.parse_args()

    prov = provenance()
    print(f"P1 · kernel-arm gate + re-score · HEAD={prov['git_sha'][:7]} "
          f"· python={prov['python']} · threads={prov['torch_num_threads']}")

    if not Q30.exists():
        raise SystemExit(
            f"{Q30} does not exist. Step A (scripts/run_q30_additive.py, unmodified) "
            "must finish first — it is the comparator, and gating against "
            "k6-designspace.json instead would be circular under D12.")

    q30_rows = json.loads(Q30.read_text())
    comparator = index_rows(q30_rows, Q30_KEYS)
    print(f"comparator: {len(comparator)} rows from {Q30}")

    k6_committed = committed_index(K6, K6_KEYS)
    k6b_committed = committed_index(K6B, K6B_KEYS)
    ctrl_k6 = committed_index(K6, K6_KEYS, arms=CONTROL_ARMS)
    ctrl_k6b = committed_index(K6B, K6B_KEYS, arms=CONTROL_ARMS)
    print(f"committed kernel rows: {len(k6_committed)} K6 + {len(k6b_committed)} K6b "
          f"= {len(k6_committed) + len(k6b_committed)}")

    pairs = _pairs(k6_committed)
    if args.limit:
        pairs = pairs[:args.limit]

    # Control plan: every `doe` campaign (0.1 s to regenerate), plus a qLogEI subsample.
    control_plan = {"doe": pairs,
                    "qlogei": pairs[:args.qlogei_control] if args.qlogei_control else []}

    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(DIM, SUBSET_N, seed=GRID_SEED)

    gate_failures: list[dict] = []
    gate_rows: list[dict] = []
    rescore_failures: list[dict] = []
    control_failures: list[dict] = []
    n_k6 = n_k6b = n_ctrl_k6 = n_ctrl_k6b = 0
    t0 = time.time()

    def snapshot(v: str = "IN_PROGRESS", coverage_error: str | None = None) -> dict:
        """The output file at any moment. Checkpointed after every pair, as
        `run_k6_designspace.py` does, so a four-hour run survives an interruption."""
        return {
            "provenance": prov,
            "question": "P1 — gate the A1 kernel arms and re-score the 2,800 committed "
                        "design-space rows that rest on them",
            "verdict": v,
            "registered_kill_condition": (
                "|delta| = 0 on all 2800 re-scored rows -> the committed kernel-arm "
                "rows are validated retroactively and Amendment A1 becomes citable. "
                "Any delta != 0 -> the committed kernel-arm rows are WITHDRAWN. Not "
                "repaired by re-running."),
            "config": {"dim": DIM, "primary_sigma": PRIMARY_SIGMA,
                       "kernel_arms": list(KERNEL_ARMS),
                       "control_arms": list(CONTROL_ARMS),
                       "qlogei_control_campaigns": args.qlogei_control,
                       "pairs": len(pairs), "gammas": list(GAMMAS),
                       "tau_fracs": list(TAU_FRACS), "grid_n": GRID_N,
                       "grid_seed": GRID_SEED, "k6b_subset_n": SUBSET_N,
                       "k6b_n_draws": N_DRAWS, "tolerance": 0.0},
            "coverage": {"gate_campaigns": len(gate_rows),
                         "rescored_k6_rows": n_k6, "rescored_k6b_rows": n_k6b,
                         "rescored_total": n_k6 + n_k6b,
                         "registered_total": REGISTERED_K6_ROWS + REGISTERED_K6B_ROWS,
                         "control_k6_rows": n_ctrl_k6, "control_k6b_rows": n_ctrl_k6b,
                         "error": coverage_error},
            "worst": {
                "gate_abs_delta": max((g["abs_delta"] for g in gate_rows), default=0.0),
                "rescore_abs_delta": max((f["abs_delta"] for f in rescore_failures),
                                         default=0.0),
                "control_abs_delta": max((f["abs_delta"] for f in control_failures),
                                         default=0.0)},
            "gate_failures": gate_failures,
            "rescore_failures": rescore_failures,
            "control_failures": control_failures,
            "gate": gate_rows,
            "elapsed_s": round(time.time() - t0, 1),
        }

    # ---------------------------------------------------------------- PASS 1 · K6
    # regenerate -> gate -> score_campaign, which is `run_k6_designspace.py`'s order.
    print(f"\nPASS 1 — K6 re-score, {len(pairs)} pairs x "
          f"{len(KERNEL_ARMS)} kernel arms (+ controls)")
    for i, (inst_id, seed) in enumerate(pairs, 1):
        inst = instance_by_id(inst_id, DIM)
        orc = BiphasicOracle(inst, sigma_rel=PRIMARY_SIGMA, seed=seed)
        with torch.no_grad():
            truth = orc.truth(grid).reshape(-1).double()

        for arm in KERNEL_ARMS + CONTROL_ARMS:
            if arm in CONTROL_ARMS and (inst_id, seed) not in control_plan[arm]:
                continue
            t = time.time()
            rec = regenerate(inst_id, DIM, PRIMARY_SIGMA, seed, arm)

            if arm in KERNEL_ARMS:
                g = gate_regret(comparator, instance=inst_id, dim=DIM,
                                sigma=PRIMARY_SIGMA, seed=seed, arm=arm,
                                regenerated=rec.regret)
                g["pass"] = "k6"
                gate_rows.append(g)
                if not g["passed"]:
                    gate_failures.append(g)
                    print(f"  !! GATE {arm} {inst_id} seed={seed} "
                          f"|d|={g['abs_delta']:.3e}")

            active = torch.zeros(DIM, dtype=torch.bool)
            if rec.kept_factors is None:
                active[:] = True
            else:
                active[list(rec.kept_factors)] = True

            target = k6_committed if arm in KERNEL_ARMS else ctrl_k6
            sink = rescore_failures if arm in KERNEL_ARMS else control_failures
            n_fail = 0
            for row in score_campaign(rec, orc, grid, truth, active):
                key = tuple(row[c] for c in K6_KEYS)
                if key not in target:
                    raise KeyError(f"re-scored a row with no committed counterpart: "
                                   f"{key}")
                f = compare_row(target[key], row, K6_KEYS)
                sink.extend(f)
                n_fail += len(f)
                if arm in KERNEL_ARMS:
                    n_k6 += 1
                else:
                    n_ctrl_k6 += 1
            tag = "CONTROL " if arm in CONTROL_ARMS else ""
            print(f"[{i:3d}/{len(pairs)}] K6  {tag}{arm:14s} {inst_id} seed={seed} "
                  f"regret={rec.regret:.4f} metric_fails={n_fail} "
                  f"({time.time() - t:.1f}s)", flush=True)
        _write(snapshot())
        del truth
        gc.collect()

    # --------------------------------------------------------------- PASS 2 · K6b
    # regenerate -> build_gp -> joint_draws, which is `run_k6b_conservative.py`'s order.
    print(f"\nPASS 2 — K6b re-score, {len(pairs)} pairs")
    for i, (inst_id, seed) in enumerate(pairs, 1):
        inst = instance_by_id(inst_id, DIM)
        orc = BiphasicOracle(inst, sigma_rel=PRIMARY_SIGMA, seed=seed)
        mu_max = float(inst.optimum_value)

        for arm in KERNEL_ARMS + CONTROL_ARMS:
            if arm in CONTROL_ARMS and (inst_id, seed) not in control_plan[arm]:
                continue
            t = time.time()
            rec = regenerate(inst_id, DIM, PRIMARY_SIGMA, seed, arm)

            if arm in KERNEL_ARMS:
                # A second, independent regeneration of the same campaign. Free here,
                # and it turns pass 2 into a determinism check on pass 1 as well.
                g = gate_regret(comparator, instance=inst_id, dim=DIM,
                                sigma=PRIMARY_SIGMA, seed=seed, arm=arm,
                                regenerated=rec.regret)
                g["pass"] = "k6b"
                gate_rows.append(g)
                if not g["passed"]:
                    gate_failures.append(g)
                    print(f"  !! GATE {arm} {inst_id} seed={seed} "
                          f"|d|={g['abs_delta']:.3e}")

            target = k6b_committed if arm in KERNEL_ARMS else ctrl_k6b
            sink = rescore_failures if arm in KERNEL_ARMS else control_failures
            n_fail = 0
            for row in score_campaign_k6b(rec, orc, X_sub, mu_max, DIM):
                key = tuple(row[c] for c in K6B_KEYS)
                if key not in target:
                    raise KeyError(f"re-scored a row with no committed counterpart: "
                                   f"{key}")
                f = compare_row(target[key], row, K6B_KEYS)
                sink.extend(f)
                n_fail += len(f)
                if arm in KERNEL_ARMS:
                    n_k6b += 1
                else:
                    n_ctrl_k6b += 1
            tag = "CONTROL " if arm in CONTROL_ARMS else ""
            print(f"[{i:3d}/{len(pairs)}] K6b {tag}{arm:14s} {inst_id} seed={seed} "
                  f"metric_fails={n_fail} ({time.time() - t:.1f}s)", flush=True)
        _write(snapshot())
        gc.collect()

    # ------------------------------------------------- PASS 3 · the gate-only cell
    # sigma_rel = 0.10 has no design-space rows anywhere, so it is gated and not scored.
    other = sorted({(r["instance"], r["sigma"], r["seed"], r["arm"]) for r in q30_rows
                    if r["sigma"] != PRIMARY_SIGMA})
    if args.limit:
        keep = {p[0] for p in pairs}
        other = [o for o in other if o[0] in keep]
    print(f"\nPASS 3 — gate-only, {len(other)} campaigns at sigma != {PRIMARY_SIGMA}")
    for j, (inst_id, sigma, seed, arm) in enumerate(other, 1):
        t = time.time()
        rec = regenerate(inst_id, DIM, sigma, seed, arm)
        g = gate_regret(comparator, instance=inst_id, dim=DIM, sigma=sigma,
                        seed=seed, arm=arm, regenerated=rec.regret)
        g["pass"] = "gate_only"
        gate_rows.append(g)
        if not g["passed"]:
            gate_failures.append(g)
            print(f"  !! GATE {arm} {inst_id} sigma={sigma} seed={seed} "
                  f"|d|={g['abs_delta']:.3e}")
        print(f"[{j:3d}/{len(other)}] gate {arm:14s} {inst_id} sigma={sigma} "
              f"seed={seed} |d|={g['abs_delta']:.3e} ({time.time() - t:.1f}s)",
              flush=True)
        _write(snapshot())

    # ------------------------------------------------------------------- the verdict
    coverage_error = None
    try:
        assert_full_coverage(rescored_k6=n_k6, rescored_k6b=n_k6b)
    except ValueError as exc:
        coverage_error = str(exc)

    v = verdict(gate_failures, rescore_failures)
    if coverage_error:
        v = "INCOMPLETE"

    payload = snapshot(v, coverage_error)
    worst_gate = payload["worst"]["gate_abs_delta"]
    worst_rescore = payload["worst"]["rescore_abs_delta"]
    worst_control = payload["worst"]["control_abs_delta"]
    _write(payload)

    print(f"\n{'=' * 78}")
    print(f"gate campaigns      : {len(gate_rows)}  failures: {len(gate_failures)}  "
          f"worst |d| = {worst_gate:.3e}")
    print(f"re-scored rows      : {n_k6} K6 + {n_k6b} K6b = {n_k6 + n_k6b}  "
          f"metric failures: {len(rescore_failures)}  worst |d| = {worst_rescore:.3e}")
    print(f"control rows        : {n_ctrl_k6} K6 + {n_ctrl_k6b} K6b  "
          f"failures: {len(control_failures)}  worst |d| = {worst_control:.3e}")
    if coverage_error:
        print(f"COVERAGE           : {coverage_error}")
    print(f"VERDICT             : {v}")
    print(f"{'=' * 78}\nwritten to {OUT}")
    if v != "VALIDATED":
        sys.exit(1)


if __name__ == "__main__":
    main()
