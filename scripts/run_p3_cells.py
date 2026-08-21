"""P3 — the three (d, sigma_rel) cells the design-space programme has never run.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a), section P3, before this file
existed. Cells: (6, 0.10), (8, 0.25), (8, 0.10). Arms: all eight.

WHY THIS RUNNER EXISTS RATHER THAN TWO INVOCATIONS OF THE COMMITTED ONES
------------------------------------------------------------------------
`scripts/run_k6_designspace.py` and `scripts/run_k6b_conservative.py` are committed and
are NOT modified. Two things stop them being simply re-invoked at the new cells:

1. **The gate.** Both contain `ref = committed.get(...)` / `if ref is not None`, the two
   lines that skipped 100 campaigns without saying so (COVERAGE-MATRIX §3.6). At d=8 the
   same lines skip `doe` as well, because `results/e2-grid.json` has **no `doe` column at
   d=8** — it is in `results/e2-doe-d8.json`. The registration makes that skip a STOP
   CONDITION, so here a missing gate target RAISES :class:`MissingGateTarget`. An arm
   that genuinely has no comparator is recorded as `gated: false` with a reason, in the
   row, never dropped.

2. **The budget.** Regeneration dominates (a `qlognei` campaign is 16–24 s against ~2 s of
   K6 scoring and ~0.8 s of K6b scoring). Running both committed scripts would regenerate
   every campaign twice and double the registered 4.1 CPU-h. Here each campaign is
   regenerated **once** and scored on both deliverables. `regenerate` is deterministic in
   `(instance, dim, sigma, seed, arm)` — K1 measured 500/500 rows at |Δ| = 0 — so one
   record and two records are the same input.

Both scorers here are re-expressions, and both are pinned to a **committed** artefact
rather than to themselves (D12). `score_k6b` reproduces `results/k6b-conservative.json`
and `k6b-conservative-spread.json` field by field; `score_k6_dual_tau`'s committed columns
are asserted bit-identical to `run_k6_designspace.score_campaign`, which is imported for
exactly that comparison and for nothing else.

AMENDMENT F (commit 07e98df) SUPERSEDES THIS FILE'S ORIGINAL STATISTICS
-----------------------------------------------------------------------
K6's scoring could not simply be imported once F landed. F2a makes the expected type I /
type II error volumes the PRIMARY design-space metric over AUC -- AUC is invariant to
monotone transformation, so it scores ranking and never calibration, and mean `grid_r2`
is negative for all eight arms, which AUC cannot see. Those volumes ARE derivable from
committed columns. **AUPRC (F2b) is not**: it needs `p_pred` and `truth`, and no stored
row carries either, which is why the registration folds F2b into a re-score rather than
an analysis. So the maps are built once here and every F column is written at source.

Erratum 3 matters more here than anywhere: `tau = tau_frac * tau_max(gamma, sigma_rel)`
and `tau_max` DECREASES in gamma, so higher gamma buys a LOWER absolute tau and an EASIER
certificate. AUC degrades at both ends of that ladder -- ~17 negative grid points of
20,000 at gamma=0.99/tau_frac=0.60, ~59 positive at gamma=0.50/tau_frac=0.95 -- while the
error volumes stay defined across all of it, including where `D_est` is empty.

P3-B2 — THE tau_max SENSITIVITY, WHICH IS NOT A FIX
----------------------------------------------------
`tau_max` omits `sigma_add` and is optimistic by 8.204e-04 at sigma_rel = 0.10. The
registered decision is that it is **NOT changed**: correcting the sigma=0.10 cells while
the committed sigma=0.25 cells keep the old definition would confound the sigma axis with
a definition change. `--sensitivity` scores the (6, 0.10) cell under BOTH definitions from
the same posterior pass and writes the pair to `results/p3-taumax-sensitivity.json`. It
touches no other output. K6b is unaffected by construction: its threshold is
`theta = tau_frac * mu_max`, which never calls `tau_max`.
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_k6_designspace import GAMMAS, GRID_N, GRID_SEED, TAU_FRACS, score_campaign  # noqa: E402
from run_k6b_conservative import (ALPHAS, JITTER, N_DRAWS, SUBSET_N,  # noqa: E402
                                  TAU_FRACS as K6B_TAU_FRACS, joint_draws)

# `boec.calibration` is the CANONICAL home for both (commit 8c45e31). This file briefly
# carried a second `error_volumes` in `designspace.py`; it is deleted rather than kept in
# sync, for the same reason a GP fit is not shared between two scorers here -- one
# committed quantity, one definition.
from boec.calibration import average_precision, error_volumes  # noqa: E402
from boec.designspace import (brier_and_auc,  # noqa: E402
                              false_inclusion_rate, gp_adapter,
                              inscribed_box_from_mask, iou,
                              predictive_probability_map, probability_map, tau_max,
                              tau_max_exact)
from boec.norms import grid_r2, sobol_grid, sup_err  # noqa: E402
from boec.replay import committed_rows, instance_by_id, regenerate, unit_bounds  # noqa: E402
from boec.surrogate import build_gp  # noqa: E402
from boec.torch_oracle import BiphasicOracle  # noqa: E402
from boec import vorobev as _vorobev  # noqa: E402
from boec.vorobev import (alpha_star, conservative_estimate,  # noqa: E402
                          empirical_containment, excursion_probability,
                          vorobev_deviation, vorobev_expectation)

ROOT = Path(__file__).resolve().parents[1]

#: All eight arms the registration names, in the order they are scored.
ARMS = ("doe", "qlogei", "qlognei", "qlogei-add", "qlogei-addonly",
        "lhs", "sobol", "random")
#: Q30's post-hoc kernel arms. `results/q30-additive.json` is P1's output; until it lands
#: these are CANNOT GATE (COVERAGE-MATRIX §3.6), and that is written into every row.
KERNEL_ARMS = ("qlogei-add", "qlogei-addonly")

GATE_GRID = ROOT / "results/e2-grid.json"
#: `e2-grid.json` carries no `doe` column at d=8. This is the audit's P3 blocker and the
#: one place a `committed.get()` would silently return None on a REAL arm.
GATE_DOE_D8 = ROOT / "results/e2-doe-d8.json"
GATE_KERNEL = ROOT / "results/q30-additive.json"
#: K1 measured every gatable arm at worst |Δ| = 0.0 over 500 rows. There is no tolerance.
GATE_TOL = 0.0


class IncompleteResult(RuntimeError):
    """An attempt to publish a partial run to a registered result path.

    Raised rather than warned. `results/p2-versionb-gamma.json` is what the alternative
    looks like: a SIGKILLed run left 8 of 50 keys, 768 rows, a full provenance block and
    `gate_failures: []`, with nothing saying it was incomplete -- and `.gitignore`
    un-ignores that path by name, so any `git add -A` would have committed a 16% run as
    the finished result.
    """


class MissingGateTarget(RuntimeError):
    """A campaign that should have been gated had no committed comparator.

    Raised rather than returned, because the failure mode this whole runner exists to
    avoid is a gate that reports success by not having run.
    """


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def _dirty() -> bool:
    return bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                               text=True).stdout.strip())


def _versions() -> dict[str, str]:
    import importlib.metadata as md
    out = {"python": platform.python_version()}
    for pkg in ("torch", "botorch", "gpytorch", "numpy", "scipy"):
        try:
            out[pkg] = md.version(pkg)
        except Exception:                                    # pragma: no cover
            out[pkg] = "unknown"
    # Erratum 2's registered remedy. The |delta| = 0 gates are now KNOWN not to be
    # thread-contingent -- P2 re-measured all 20 numeric K6 columns at all 24 cells at
    # exactly 0.0 under set_num_threads(1) and after deliberately burning the global torch
    # RNG -- so this is documentation, not a control variable. It is recorded because
    # nothing in the repository recorded it before, not because it is expected to matter.
    out["torch_num_threads"] = str(torch.get_num_threads())
    out["omp_num_threads"] = os.environ.get("OMP_NUM_THREADS", "unset")
    return out


# --- the gate -------------------------------------------------------------------------

def gate_target(arm: str, dim: int) -> Path:
    """Which committed file carries this arm's regret column at this dimension."""
    if arm in KERNEL_ARMS:
        return GATE_KERNEL
    if arm == "doe" and dim == 8:
        return GATE_DOE_D8
    return GATE_GRID


def build_gate_index(dim: int, sigma: float, arms=ARMS,
                     targets: dict[str, Path] | None = None
                     ) -> tuple[dict[tuple[str, int, str], float], dict[str, str]]:
    """``{(instance, seed, arm): committed regret}`` plus the arms that have no comparator.

    Raises:
        MissingGateTarget: if an arm whose target file **exists** contributes no rows at
            this cell. That is the §3.6 defect: the file is there, the key is not, and
            ``.get()`` would hand back ``None``.

    Returns:
        The index, and ``{arm: reason}`` for arms that are ungatable *by construction*
        because their target file does not exist. Only the kernel arms may appear there,
        and only until P1 commits ``results/q30-additive.json``.
    """
    index: dict[tuple[str, int, str], float] = {}
    ungated: dict[str, str] = {}

    for arm in arms:
        path = (targets or {}).get(arm) or gate_target(arm, dim)
        shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if not path.exists():
            if arm in KERNEL_ARMS:
                ungated[arm] = (f"{shown} absent — CANNOT GATE "
                                f"(Amendment A1 / P1; COVERAGE-MATRIX §3.6)")
                continue
            raise MissingGateTarget(
                f"gate target {path} for arm {arm!r} does not exist")

        rows = json.loads(path.read_text())
        rows = rows.get("rows", rows) if isinstance(rows, dict) else rows
        hits = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma
                and r["arm"] == arm]
        if not hits:
            # The ONE narrow exemption. `scripts/run_q30_additive.py` is committed at
            # DIM = 6 with two arms, so `results/q30-additive.json` carries d=6 only and
            # no d=8 kernel-arm column exists or is coming. That absence is a registered
            # fact, so it is recorded as an explicit `gated: false` rather than aborting
            # the cell. Every other missing target stays a hard error -- the exemption is
            # keyed on the arm, never on "the file happened to be short".
            if arm in KERNEL_ARMS:
                ungated[arm] = (f"{shown} carries no d={dim} sigma={sigma} rows — "
                                f"CANNOT GATE. run_q30_additive.py is committed at "
                                f"DIM = 6, so no d=8 kernel-arm column exists or is "
                                f"coming (Amendment A1 / P1 erratum)")
                continue
            raise MissingGateTarget(
                f"no committed rows for arm {arm!r} at d={dim} sigma={sigma} in "
                f"{shown} — a silent skip here is the §3.6 defect")
        for r in hits:
            index[(r["instance"], r["seed"], arm)] = r["regret"]

    return index, ungated


def check_gate(rec, index, ungated: dict[str, str] | None = None) -> dict:
    """Compare one regenerated campaign to its committed column. Never skips.

    Raises:
        MissingGateTarget: the arm has a comparator file but not this ``(instance, seed)``.
    """
    ungated = ungated or {}
    if rec.arm in ungated:
        return {"gated": False, "reason": ungated[rec.arm],
                "committed": None, "abs_delta": None}

    key = (rec.instance, rec.seed, rec.arm)
    if key not in index:
        raise MissingGateTarget(
            f"no committed regret for {key} in "
            f"{gate_target(rec.arm, rec.dim).name}; refusing to score an ungated campaign")
    ref = index[key]
    return {"gated": True, "reason": None, "committed": ref,
            "abs_delta": abs(rec.regret - ref)}


# --- K6b, re-expressed from run_k6b_conservative.main and pinned to its committed rows --

@contextlib.contextmanager
def _memoised_containment():
    """Compute each DISTINCT ``containment_probability`` once, within one campaign.

    **Not an approximation and not a second estimator.** ``alpha_star`` and
    ``conservative_estimate`` are called unchanged; every distinct call still reaches the
    real :func:`boec.vorobev.containment_probability` and a hit returns the float that
    function computed. Found and measured by the P2 worker; adopted here because this
    scorer pays the identical cost.

    **Why the calls repeat.** ``alpha_star`` scans ``torch.linspace(0, 1, 64)`` and
    ``conservative_estimate`` scans ``torch.linspace(1, 0, 64)``, and those two tensors
    are elementwise equal, so one ``alpha_star`` plus three ``conservative_estimate``
    calls walk the SAME 64 Vorob'ev quantiles of the SAME coverage function four times.
    ``containment_probability`` copies ``draws[:, mask]`` -- up to 512 x 2,000 doubles --
    on every one of them.

    **Why the key is safe.** ``(theta, the mask's exact bytes)``: no collision is
    possible, and the scope is one campaign, entered and left inside :func:`score_k6b`,
    which is exactly the region over which ``draws`` is fixed. A mask from one
    ``tau_frac`` cannot answer for another because ``theta`` is in the key.

    The proof is the existing gate: ``score_k6b`` still reproduces the committed
    ``k6b-conservative.json`` rows at exact float equality with this active.
    """
    real = _vorobev.containment_probability
    cache: dict[tuple[float, bytes], float] = {}

    def memoised(draws, mask, theta):
        key = (float(theta), mask.detach().cpu().numpy().tobytes())
        if key not in cache:
            cache[key] = real(draws, mask, theta)
        return cache[key]

    _vorobev.containment_probability = memoised
    try:
        yield
    finally:
        _vorobev.containment_probability = real


def score_k6b(rec, orc, X_sub: torch.Tensor, mu_max: float) -> list[dict]:
    """The four ``tau_frac`` rows of K6b for one regenerated campaign.

    Verbatim arithmetic from ``scripts/run_k6b_conservative.py``'s main loop, including
    Amendment B3's active-subspace pinning and the campaign seed for the joint draw.
    ``tests/test_p3_cells.py`` asserts equality against the committed primary-cell rows.
    """
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))

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
    with _memoised_containment():
      for tf in K6B_TAU_FRACS:
          theta = tf * mu_max
          p = excursion_probability(draws, theta)
          q = vorobev_expectation(p, draws, theta)
          true_set = truth_eval >= theta
          inter = int((q & true_set).sum())
          union = int((q | true_set).sum())
          row = {"instance": rec.instance, "dim": rec.dim, "sigma": rec.sigma,
                 "seed": rec.seed, "arm": rec.arm, "regret": rec.regret,
                 "tau_frac": tf, "theta": theta,
                 "true_frac_above": float(true_set.double().mean()),
                 "n_active": (rec.dim if rec.kept_factors is None
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
              row[f"ce_false_in_{a}"] = (float((truth_eval[ce] < theta).double().mean())
                                         if n_ce else float("nan"))
              # Looked up off the module, so inside the cache scope this IS the memo --
              # and that is exactly why the value is unchanged: `conservative_estimate`
              # has just selected on this same `(theta, ce)`, so the memo returns the
              # float the real function computed moments earlier, not a recomputation.
              # With no cache live it is the real function. The committed
              # `k6b-conservative.json` rows reproduce at exact float equality either way.
              row[f"ce_contain_{a}"] = (_vorobev.containment_probability(draws, ce, theta)
                                        if n_ce else float("nan"))
              emp = empirical_containment(ce, truth_eval, theta)
              row[f"ce_empirical_{a}"] = float("nan") if emp is None else float(emp)
          rows.append(row)

    del model, draws
    gc.collect()
    return rows


# --- P3-B2: the same campaign under both tau definitions -------------------------------

def score_k6_dual_tau(rec, orc, grid: torch.Tensor, truth: torch.Tensor,
                      active: torch.Tensor,
                      dual: bool = True) -> tuple[list[dict], list[dict]]:
    """K6 rows under ``tau_max`` and under ``tau_max_exact``, from one posterior pass.

    The first list is bit-identical to ``run_k6_designspace.score_campaign`` — the
    sensitivity may not move the baseline it is measured against, and
    ``tests/test_p3_cells.py`` asserts that equality field by field.
    """
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, X):
            return mean, sd

    m = _M()
    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    base = {"instance": rec.instance, "dim": rec.dim, "sigma": rec.sigma,
            "seed": rec.seed, "arm": rec.arm, "regret": rec.regret,
            "sup_err": sup_err(m, lambda X: truth, grid),
            "grid_r2": grid_r2(m, lambda X: truth, grid)}

    def _rows_at(tmax: float, gamma: float, tf: float) -> dict:
        tau = round(tf * tmax, 10)
        p_pred = predictive_probability_map(m, grid, tau, sigma_pred)
        p_lat = probability_map(m, grid, tau)
        d_gamma = p_pred >= gamma
        latent = p_lat >= gamma
        true_set = truth.reshape(-1) >= tau
        b_pred, a_pred = brier_and_auc(p_pred, truth, tau)
        b_lat, a_lat = brier_and_auc(p_lat, truth, tau)
        _, box_vol = inscribed_box_from_mask(grid, d_gamma, active=active,
                                             seed_score=p_pred)
        # --- the committed K6 columns. Bit-identical to run_k6_designspace.score_campaign,
        # --- asserted field by field in tests/test_p3_cells.py. Nothing below may edit it.
        row = {**base, "gamma": gamma, "tau_frac": tf, "tau": tau, "tau_max": tmax,
               "true_frac_above_tau": float(true_set.double().mean()),
               "vol_pred": float(d_gamma.double().mean()),
               "vol_latent": float(latent.double().mean()),
               "empty_pred": int(d_gamma.sum()) == 0,
               "empty_latent": int(latent.sum()) == 0,
               "iou_pred": iou(d_gamma, truth, tau),
               "iou_latent": iou(latent, truth, tau),
               "fi_pred": false_inclusion_rate(d_gamma, truth, tau),
               "fi_latent": false_inclusion_rate(latent, truth, tau),
               "brier_pred": b_pred, "auc_pred": a_pred,
               "brier_latent": b_lat, "auc_latent": a_lat,
               "box_vol_pred": box_vol,
               "n_active": int(active.sum())}

        # --- AMENDMENT F, added beside them, never in place of them -------------------
        # F2a: the PRIMARY metric. Derived, so it cannot disagree with the columns above,
        # and defined on the 54-69% of cells where an empty D_est makes fi and iou nan.
        prevalence = row["true_frac_above_tau"]
        for suffix, vol_key, fi_key in (("pred", "vol_pred", "fi_pred"),
                                        ("latent", "vol_latent", "fi_latent")):
            for k, v in error_volumes(row[vol_key], row[fi_key], prevalence).items():
                row[f"{k}_{suffix}"] = v
        # F2b: AUPRC beside AUC, primary wherever minority prevalence < 0.01. Needs the
        # raw maps, which exist only here -- no stored row carries them, which is why the
        # registration folds F2b into a re-score rather than an analysis. `None` when a
        # class is absent; 1.0 would average in as if it were skill.
        minority = min(prevalence, 1.0 - prevalence)
        for name, pm in (("pred", p_pred), ("latent", p_lat)):
            ap = average_precision(pm, truth, tau)
            row[f"auprc_{name}"] = ap
            # At HIGH gamma the minority class is the NEGATIVE one -- Erratum 3 again:
            # tau_max decreases in gamma, so gamma=0.99 tau_frac=0.60 leaves ~17 negative
            # points of 20,000 and a positive-class AP is trivially ~1 exactly where F2b
            # calls it primary. Score the complement EXPLICITLY: `-truth >= -tau` would
            # put a grid point with truth exactly tau in BOTH classes.
            row[f"auprc_minority_{name}"] = (
                ap if prevalence <= 0.5
                else average_precision(1.0 - pm, (truth < tau).double(), 0.5))
            # A no-skill ranker scores the PREVALENCE, not 0.5, so AP is not comparable
            # across cells whose prevalence runs 0.0012 to 0.999 unless this travels.
            row[f"auprc_baseline_{name}"] = minority
        row["minority_prevalence"] = minority
        row["minority_class"] = 1 if prevalence <= 0.5 else 0
        row["auprc_is_primary"] = bool(minority < 0.01)
        return row

    std, exact = [], []
    for gamma in GAMMAS:
        t_std = tau_max(gamma, orc.sigma_rel)
        t_exa = tau_max_exact(gamma, orc.sigma_rel, orc.sigma_add)
        for tf in TAU_FRACS:
            std.append(_rows_at(t_std, gamma, tf))
            if dual:
                exact.append(_rows_at(t_exa, gamma, tf))

    del model, mean, sd
    gc.collect()
    return std, exact


# --- the cell run ----------------------------------------------------------------------

def promote(scratch: Path, out: Path) -> None:
    """Publish a finished run to its registered result path. Refuses a partial.

    The completeness check reads the file being published rather than trusting the
    caller, so the guarantee survives a caller that gets its own bookkeeping wrong.
    """
    d = json.loads(scratch.read_text())
    if d.get("status") != "complete" or d.get("keys_present") != d.get("keys_expected"):
        raise IncompleteResult(
            f"refusing to publish {scratch} to {out}: status={d.get('status')!r} "
            f"keys {d.get('keys_present')}/{d.get('keys_expected')}")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(scratch.read_text())
    os.replace(tmp, out)


def _write(path: Path, head: str, dirty: bool, cfg: dict, gate_fail: list,
           ungated: dict, rows: list, started: str, *, status: str,
           keys_present: int, keys_expected: int) -> None:
    """Checkpoint one cell. **Atomic**, because this box SIGKILLs processes.

    A kill part-way through a 20 MB `write_text` leaves a truncated JSON that is not a
    partial result but a corrupt one -- and it would have overwritten the last good
    checkpoint. Writing to a temp file in the same directory and `os.replace`-ing it is
    atomic on POSIX, so a kill at any instant leaves either the previous checkpoint or
    the new one, never a half-written file.

    Every file carries ``status`` / ``complete`` / ``keys_present`` / ``keys_expected``
    at the TOP LEVEL, so a partial can never be silently consumed as a finished run --
    the defect `results/p2-versionb-gamma.json` demonstrates. ``status`` is one of
    ``in_progress``, ``complete`` or ``smoke``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({
        "status": status,
        "complete": status == "complete" and keys_present == keys_expected,
        "keys_present": keys_present,
        "keys_expected": keys_expected,
        "provenance": {"git_sha": head, "git_dirty": dirty,
                       "generated_at": started, "argv": sys.argv, **_versions()},
        "config": cfg,
        "gate_policy": {"tolerance": GATE_TOL,
                        "targets": {a: str(gate_target(a, cfg["dim"])
                                           .relative_to(ROOT)) for a in cfg["arms"]},
                        "ungated_arms": ungated},
        "gate_failures": gate_fail, "rows": rows}, indent=2))
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--sigma", type=float, required=True)
    ap.add_argument("--k6-out", type=str, required=True)
    ap.add_argument("--k6b-out", type=str, required=True)
    ap.add_argument("--sensitivity-out", type=str, default=None,
                    help="P3-B2 only; scores the cell under tau_max_exact as well")
    ap.add_argument("--limit", type=int, default=None,
                    help="smoke runs only. A limited run is now MECHANICALLY incapable "
                         "of producing a committable result: it writes to scratch, its "
                         "status is 'smoke', and it never promotes.")
    ap.add_argument("--scratch", type=str, default=None,
                    help="where partial checkpoints live. Default $TMPDIR/p3-partials. "
                         "Deliberately OUTSIDE results/, which .gitignore un-ignores by "
                         "name, so no `git add -A` can sweep up an unfinished run.")
    ap.add_argument("--arms", type=str, default=None)
    args = ap.parse_args()

    torch.set_num_threads(1)
    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    k6_out, k6b_out = Path(args.k6_out), Path(args.k6b_out)
    sens_out = Path(args.sensitivity_out) if args.sensitivity_out else None
    scratch_dir = Path(args.scratch) if args.scratch else (
        Path(os.environ.get("TMPDIR", "/tmp")) / "p3-partials")
    scratch_dir.mkdir(parents=True, exist_ok=True)

    def _scratch_for(out: Path) -> Path:
        return scratch_dir / out.name
    head, dirty = _head(), _dirty()
    started = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    print(f"P3 · cell d={args.dim} sigma={args.sigma} · HEAD={head}")
    print(f"arms={arms}")
    print(f"gamma={GAMMAS} tau_frac={TAU_FRACS} grid={GRID_N}@{GRID_SEED}")
    print(f"K6b: subset={SUBSET_N} draws={N_DRAWS} alphas={ALPHAS} jitter={JITTER}")

    index, ungated = build_gate_index(args.dim, args.sigma, arms)
    for arm in arms:
        tgt = gate_target(arm, args.dim)
        n = len([1 for k in index if k[2] == arm])
        print(f"  gate {arm:15s} <- {tgt.name:20s} {n:3d} rows"
              + ("  ** UNGATED: " + ungated[arm] if arm in ungated else ""))

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == args.dim and r["sigma"] == args.sigma
                   and r["arm"] == "qlogei"})
    if args.limit:
        keys = keys[:args.limit]
        print(f"\n*** SMOKE RUN, {len(keys)} keys. Not a committable result. ***")
    print(f"\n{len(keys)} (instance, seed) pairs x {len(arms)} arms "
          f"= {len(keys)*len(arms)} campaigns\n", flush=True)

    grid = sobol_grid(args.dim, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(args.dim, SUBSET_N, seed=GRID_SEED)

    k6_rows: list[dict] = []
    k6b_rows: list[dict] = []
    sens_rows: list[dict] = []
    gate_fail: list[dict] = []
    t0 = time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, args.dim)
        orc = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
        mu_max = float(inst.optimum_value)
        with torch.no_grad():
            truth = orc.truth(grid).reshape(-1).double()

        for arm in arms:
            t = time.time()
            rec = regenerate(inst_id, args.dim, args.sigma, seed, arm)

            verdict = check_gate(rec, index, ungated)
            if verdict["gated"] and verdict["abs_delta"] > GATE_TOL:
                gate_fail.append({"instance": inst_id, "seed": seed, "arm": arm,
                                  "committed": verdict["committed"],
                                  "regenerated": rec.regret,
                                  "abs_delta": verdict["abs_delta"],
                                  "target": gate_target(arm, args.dim).name})
                print(f"  !! GATE {arm} {inst_id} seed={seed} "
                      f"delta={verdict['abs_delta']:.3e}", flush=True)

            active = torch.zeros(args.dim, dtype=torch.bool)
            if rec.kept_factors is None:
                active[:] = True
            else:
                active[list(rec.kept_factors)] = True

            stamp = {"gated": verdict["gated"], "gate_target": (
                gate_target(arm, args.dim).name if verdict["gated"] else None),
                "gate_reason": verdict["reason"]}

            # ONE scoring path for every cell. Amendment F requires type I/II volumes
            # and AUPRC on every row, and AUPRC is NOT derivable after the fact -- it
            # needs p_pred and truth, which no stored row carries. So the P3 scorer is
            # used everywhere and `run_k6_designspace.score_campaign` is kept as the
            # thing it is pinned to, field by field, in tests/test_p3_cells.py.
            std, exact = score_k6_dual_tau(rec, orc, grid, truth, active,
                                           dual=sens_out is not None)
            k6_rows.extend({**r, **stamp} for r in std)
            if sens_out is not None:
                sens_rows.extend([{**r, **stamp, "tau_definition": "tau_max"}
                                  for r in std]
                                 + [{**r, **stamp, "tau_definition": "tau_max_exact"}
                                    for r in exact])

            k6b_rows.extend({**r, **stamp} for r in score_k6b(rec, orc, X_sub, mu_max))

            print(f"[{i:3d}/{len(keys)}] {arm:14s} {inst_id} seed={seed} "
                  f"regret={rec.regret:.4f} active={int(active.sum())} "
                  f"gated={verdict['gated']} ({time.time()-t:.1f}s)", flush=True)

        cfg = {"dim": args.dim, "sigma": args.sigma, "arms": list(arms),
               "gammas": list(GAMMAS), "tau_fracs": list(TAU_FRACS),
               "grid_n": GRID_N, "grid_seed": GRID_SEED,
               "smoke_limit": args.limit}
        # Checkpoint to SCRATCH, never to the registered result path. The results path
        # is written exactly once, whole, at the end -- see the promotion block below.
        done = i == len(keys)
        st = "smoke" if args.limit else ("complete" if done else "in_progress")
        # K6b is gamma-free by construction -- theta = tau_frac * mu_max absorbs margin 1
        # exactly -- so `gammas` and `grid_n` are dropped rather than carried as null.
        k6b_cfg = {k: v for k, v in cfg.items() if k not in ("gammas", "grid_n")}
        marks = dict(status=st, keys_present=i, keys_expected=len(keys))
        _write(_scratch_for(k6_out), head, dirty, cfg, gate_fail, ungated, k6_rows,
               started, **marks)
        _write(_scratch_for(k6b_out), head, dirty,
               {**k6b_cfg, "tau_fracs": list(K6B_TAU_FRACS), "alphas": list(ALPHAS),
                "subset_n": SUBSET_N, "n_draws": N_DRAWS, "jitter": JITTER},
               gate_fail, ungated, k6b_rows, started, **marks)
        if sens_out is not None:
            _write(_scratch_for(sens_out), head, dirty,
                   {**cfg, "sensitivity": "P3-B2 tau_max vs tau_max_exact",
                    "sigma_add": 0.01}, gate_fail, ungated, sens_rows, started, **marks)
        del truth
        gc.collect()

    print(f"\nK6 {len(k6_rows)} rows · K6b {len(k6b_rows)} rows"
          + (f" · sensitivity {len(sens_rows)} rows" if sens_out else "")
          + f" in {time.time()-t0:.0f}s")
    print(f"gate failures: {len(gate_fail)}")
    if gate_fail:
        print("*** Regenerated campaigns did not reproduce. STOP CONDITION 1. ***")
        sys.exit(1)

    if args.limit:
        print(f"\nSMOKE RUN ({args.limit} keys) — NOT promoted. Partials in "
              f"{scratch_dir}, status='smoke'. Nothing was written to results/.")
        return

    outs = [k6_out, k6b_out] + ([sens_out] if sens_out else [])
    for out in outs:
        promote(_scratch_for(out), out)
        print(f"published: {out}")


if __name__ == "__main__":
    main()
