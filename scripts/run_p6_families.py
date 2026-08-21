"""P6 · family coverage — the design space off the Hill oracle, at `tau_q`.

    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
      .venv/bin/python -u scripts/run_p6_families.py --family levy --dim 6 --sigma 0.25

**BLOCKED.** P6 does not run until Amendment F's analysis half (F2a / F2c / F4) is
committed. The binary exists first so that F's columns are in the schema from the first
row written, which is the one thing that cannot be repaired afterwards -- see below.

WHY THIS FILE EXISTS BEFORE IT IS ALLOWED TO RUN
------------------------------------------------
**F2b's AUPRC is not derivable after the fact.** It needs the full `p_pred` vector and the
truth labels over the 20,000-point grid, and no stored row carries either.
`results/p4-coord.json` is committed with 1,400 rows and no AUPRC because the brief that
produced it predated F2b, and recovering it means re-running every campaign.
`true_frac_above_tau` is the same class of omission -- it is why `results/versionb.json`
is unscoreable to this day. Both are in the schema here.

THE THRESHOLD IS `tau_q`, AND THAT CHANGES WHAT gamma DOES
-----------------------------------------------------------
Under the committed `tau_frac` grid, `tau = tau_frac * tau_max(gamma, sigma)`, so gamma set
the threshold AND the certification level at once. `tau_q` (P5) sets the threshold by
prevalence instead, so on this grid **gamma sets only the certification level** and the
true superlevel set covers the same fraction `p` of the box on every family. That is the
whole point: at one `tau_frac` the true set covers 0.00000 of the box on ackley and 0.95550
on rosenbrock, which is not a comparison.

`tau_max` therefore no longer bounds `tau` automatically, so it is recorded on every row
together with `tau_above_ceiling`. A region that is empty because `tau` sits above the
predictive ceiling is empty for a reason that has nothing to do with the design, and
without the flag that reads as an arm certifying nothing.

WHAT IS GATED, AND THE ONE COLUMN THAT IS ALMOST RIGHT
------------------------------------------------------
| arm | committed column | families |
|---|---|---|
| `qlogei` | `q42-families.json · bo_a` (cross-checked against `d20-rescore.json · bo_a`) | all four |
| `doe` | `d20-rescore.json · doe_a_new` | all four |
| `qlognei` | `q59-hartmann-no-screen.json · rows[].arms.qlognei.rule_a` | **hartmann6 d=6 only** |
| `lhs`/`sobol`/`random` | **none exists** | ungatable off Hill, recorded per row |

**`doe` does NOT gate on `q42-families.json · doe_a`**, which scored the classical arm by
oracle-best while `bo_a` on the line above used rule A. That column is carried anyway, as
`superseded_column`, and every row records whether the two committed columns even differ.
They agree on **22 of 25 ackley rows** and 15 of 25 hartmann6 rows at d=6 sigma=0.25
(Erratum 4), so a gate silently pointed at the wrong one would pass on most rows and be
wrong, and a spot-check on the first few seeds would not notice. Asserting only that the
right column reproduces cannot detect that; asserting both halves can.

ACKLEY IS IN, AS A DECLARED SENSITIVITY, NEVER A HEADLINE
----------------------------------------------------------
Under `tau_q` its superlevel set is non-empty by construction, so the `CANNOT RUN` verdict
dissolves -- it was a property of the threshold, not of the family. Two reasons survive the
fix: the CCD evaluates the box centre, which is ackley's exact optimum, and the DoE arm
attains the optimum in 7 of 25 instances. Every ackley row carries `sensitivity: true`.

IDENTITY: `family`, NEVER `instance`
------------------------------------
Off Hill, `replay.regenerate` sets `CampaignRecord.instance` to the family label, so a
consumer reading `instance` alone cannot tell a family from a Hill landscape id. This
runner does not emit the key at all. Rows are keyed by :data:`ROW_KEY`.
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.calibration import average_precision, error_volumes        # noqa: E402
from boec.designspace import (brier_and_auc, false_inclusion_rate,   # noqa: E402
                              gp_adapter, inscribed_box_from_mask, iou,
                              predictive_probability_map, probability_map, tau_max)
from boec.norms import grid_r2, sobol_grid, sup_err                  # noqa: E402
from boec.replay import FAMILY_ORACLE, regenerate, unit_bounds       # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402

OUT = ROOT / "results" / "p6-families.json"
TAU_TABLE = ROOT / "results/p5-tau-quantile.json"
GATE_Q42 = ROOT / "results" / "q42-families.json"
GATE_D20 = ROOT / "results" / "d20-rescore.json"
GATE_Q59 = ROOT / "results" / "q59-hartmann-no-screen.json"

FAMILIES = tuple(FAMILY_ORACLE)
ARMS = ("doe", "qlogei", "qlognei", "lhs", "sobol", "random")
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
#: The registered grid, identical to `run_k6_designspace.py:57-58` and to P5's.
GRID_N, GRID_SEED = 20_000, 0
N_SEEDS = 25
#: Rows are keyed by this and nothing else. `instance` is deliberately absent.
ROW_KEY = ("family", "dim", "sigma", "seed", "arm")
#: The only family that is a declared sensitivity rather than a headline.
SENSITIVITY_FAMILIES = ("ackley",)

_SPREAD_REASON = (
    "no committed family column exists for {arm!r} on any family -- lhs/sobol/random are "
    "ungatable off hill (COVERAGE-MATRIX B4). Reproducibility is the RNG's: one "
    "static_design call and one evaluate call, both seeded.")
_QLOGNEI_REASON = (
    "q59-hartmann-no-screen.json is the only committed qlognei family column and it is "
    "hartmann6 at d=6 only; {family} d={dim} has no comparator and none is coming, so "
    "this arm is UNGATABLE at this cell.")


class MissingGateTarget(RuntimeError):
    """A campaign that cannot be gated is not scored. Never a silent skip.

    COVERAGE-MATRIX §3.6: ``committed.get(...)`` returned ``None``, ``if ref is not None``
    swallowed it, and 100 campaigns lost their gate with nothing in the output saying so.
    """


# ======================================================================================
# tau -- READ from the committed table, never recomputed
# ======================================================================================
@dataclass(frozen=True)
class Tau:
    """One registered threshold, exactly as `results/p5-tau-quantile.json` committed it."""

    family: str
    dim: int
    p: float
    tau: float
    #: P5 stores this MEASURED. Amendment F2a's `type_II_vol = true_frac_above_tau -
    #: intersect` needs it, and Erratum 3 requires it beside every prevalence-sensitive
    #: number. It is re-measured per campaign against the same grid and the two must agree.
    true_frac_above_tau: float
    sensitivity: bool


_TAU_INDEX: dict[tuple[str, int, float], Tau] | None = None


def _tau_index() -> dict[tuple[str, int, float], Tau]:
    global _TAU_INDEX
    if _TAU_INDEX is None:
        doc = json.loads(TAU_TABLE.read_text())
        idx = {}
        for r in doc["rows"]:
            if r["family"] == "hill":       # hill is per-instance and is not a P6 family
                continue
            idx[(r["family"], r["dim"], r["p"])] = Tau(
                family=r["family"], dim=r["dim"], p=r["p"], tau=r["tau_q"],
                true_frac_above_tau=r["true_frac_above_tau"],
                sensitivity=bool(r["sensitivity"]))
        _TAU_INDEX = idx
    return _TAU_INDEX


def tau_for(family: str, dim: int, p: float) -> Tau:
    """The committed `tau_q`. Raises rather than recomputing a cell the table lacks."""
    try:
        return _tau_index()[(family, dim, p)]
    except KeyError:
        raise KeyError(
            f"no committed tau_q for family={family!r} d={dim} p={p!r} in "
            f"{TAU_TABLE.relative_to(ROOT)}; P5 registers p in "
            f"{sorted({k[2] for k in _tau_index()})} and families "
            f"{sorted({k[0] for k in _tau_index()})}") from None


def registered_p(family: str, dim: int) -> tuple[float, ...]:
    """The four registered prevalences, in the order P5 committed them."""
    return tuple(k[2] for k in _tau_index() if k[0] == family and k[1] == dim)


def above_ceiling(tau: float, gamma: float, sigma: float) -> bool:
    """Does this tau sit above the predictive ceiling at this (gamma, sigma)?

    `tau_max` is unchanged and unmodified (P3-B2); it is consulted, never re-registered.
    Above it, `D_gamma` is empty because of the noise floor and not because of the design,
    and a table that does not say so invites the opposite reading.
    """
    return tau > tau_max(gamma, sigma)


# ======================================================================================
# GATES -- both halves, and an ungatable arm is recorded rather than dropped
# ======================================================================================
def _rows(path: Path) -> list[dict]:
    if not path.exists():
        raise MissingGateTarget(f"gate target {path} does not exist")
    doc = json.loads(path.read_text())
    return doc["rows"] if isinstance(doc, dict) else doc


def build_gate_index(family: str, dim: int, sigma: float, arms=ARMS):
    """``({(arm, seed): committed}, {(arm, seed): superseded}, {arm: reason})``.

    Raises:
        MissingGateTarget: an arm whose comparator file exists contributes no rows at
            this cell. Only arms ungatable **by construction** reach ``ungated``.
    """
    q42 = {(r["family"], r["dim"], r["sigma"], r["seed"]): r for r in _rows(GATE_Q42)}
    d20 = {(r["family"], r["dim"], r["sigma"], r["seed"]): r for r in _rows(GATE_D20)}
    index: dict[tuple[str, int], float] = {}
    superseded: dict[tuple[str, int], float] = {}
    ungated: dict[str, str] = {}

    for arm in arms:
        if arm in ("lhs", "sobol", "random"):
            ungated[arm] = _SPREAD_REASON.format(arm=arm)
            continue

        if arm == "qlognei":
            if family != "hartmann6" or dim != 6:
                ungated[arm] = _QLOGNEI_REASON.format(family=family, dim=dim)
                continue
            hits = [r for r in _rows(GATE_Q59) if r["sigma"] == sigma]
            if not hits:
                raise MissingGateTarget(
                    f"{GATE_Q59.name} carries no sigma={sigma} rows -- a silent skip "
                    "here is the COVERAGE-MATRIX §3.6 defect")
            for r in hits:
                index[(arm, r["seed"])] = r["arms"]["qlognei"]["rule_a"]
            continue

        # `qlogei` and `doe` both key on (family, dim, sigma, seed) in both files.
        keys = [k for k in d20 if k[:3] == (family, dim, sigma)]
        if not keys:
            raise MissingGateTarget(
                f"no committed rows for {family!r} d={dim} sigma={sigma} in "
                f"{GATE_D20.name} -- refusing to score an ungated cell")
        for k in keys:
            seed = k[3]
            if arm == "qlogei":
                ref = q42[k]["bo_a"]
                # Two committed files claim to carry the same column. If they ever
                # disagree, one of them is not what its name says and no gate built on
                # either is meaningful.
                if d20[k]["bo_a"] != ref:
                    raise MissingGateTarget(
                        f"{GATE_Q42.name} and {GATE_D20.name} disagree on bo_a at {k}: "
                        f"{ref!r} vs {d20[k]['bo_a']!r}")
                index[(arm, seed)] = ref
            else:                                    # doe
                index[(arm, seed)] = d20[k]["doe_a_new"]
                # The PRE-D20 column, kept so it can be shown wrong rather than assumed
                # wrong. It scored this arm by oracle-best while bo_a used rule A.
                superseded[(arm, seed)] = q42[k]["doe_a"]

    return index, superseded, ungated


def count_distinguishing(family: str, dim: int, sigma: float, arm: str = "doe") -> int:
    """Seeds at which the right committed column and the superseded one actually differ.

    The count floor this feeds is **per family**, never pooled: 3 of 25 on ackley against
    19 of 25 on rosenbrock at d=6 sigma=0.25, so a pooled floor would be satisfied by
    rosenbrock alone and vacuous exactly where the risk is highest.
    """
    index, superseded, _ = build_gate_index(family, dim, sigma)
    return sum(1 for k, v in superseded.items()
               if k[0] == arm and index.get(k) != v)


def check_gate(rec, index, superseded, ungated) -> dict:
    """Compare one regenerated campaign to its committed column. Never skips."""
    if rec.arm in ungated:
        return {"gated": False, "reason": ungated[rec.arm], "committed": None,
                "abs_delta": None, "superseded_column": None,
                "superseded_abs_delta": None, "distinguishes": None}

    key = (rec.arm, rec.seed)
    if key not in index:
        raise MissingGateTarget(
            f"no committed regret for {rec.family} d={rec.dim} sigma={rec.sigma} "
            f"{key}; refusing to score an ungated campaign")

    ref = index[key]
    sup = superseded.get(key)
    return {"gated": True, "reason": None, "committed": ref,
            "abs_delta": abs(rec.regret - ref),
            "superseded_column": sup,
            "superseded_abs_delta": None if sup is None else abs(rec.regret - sup),
            "distinguishes": None if sup is None else sup != ref}


# ======================================================================================
# SCORING
# ======================================================================================
def row_identity(family: str, dim: int, sigma: float, seed: int, arm: str) -> dict:
    """The five keys a row is identified by, plus the sensitivity flag. No `instance`."""
    return {"family": family, "dim": dim, "sigma": sigma, "seed": seed, "arm": arm,
            "sensitivity": family in SENSITIVITY_FAMILIES}


def _ap_pair(p: torch.Tensor, truth: torch.Tensor, tau: float,
             positive_frac: float) -> tuple[float | None, float | None, float]:
    """``(AP of the positive class, AP of the MINORITY class, minority prevalence)``.

    **Erratum 5b.** gamma enters `tau` multiplicatively through `tau_max`, so a high gamma
    means a LOW absolute threshold and a huge positive class -- and a positive-class AP is
    then trivially ~1 exactly where F2b flags it as primary. At gamma=0.99, tau_frac=0.60
    about 16 of 20,000 grid points are NEGATIVE.

    The complement is scored by relabelling rather than by a second implementation: the
    canonical :func:`boec.calibration.average_precision` is called on ``1 - p`` against a
    synthetic 0/1 truth thresholded at 0.5, so there are no ties at the threshold and no
    inequality to get backwards.
    """
    ap = average_precision(p, truth, tau)
    minority_frac = min(positive_frac, 1.0 - positive_frac)
    if positive_frac <= 0.5:
        return ap, ap, minority_frac
    flipped = torch.where(truth.reshape(-1) >= tau, 0.0, 1.0).double()
    return ap, average_precision(1.0 - p, flipped, 0.5), minority_frac


def map_row(m, grid: torch.Tensor, truth: torch.Tensor, *, tau: float, gamma: float,
            sigma_pred: torch.Tensor, active: torch.Tensor) -> dict:
    """Every map metric at one ``(gamma, tau)``. Pure: no GP fit, no oracle, no campaign.

    Split out from :func:`score_campaign` precisely so the Amendment F arithmetic can be
    tested on a posterior the test writes by hand, in milliseconds, without a campaign.
    """
    p_pred = predictive_probability_map(m, grid, tau, sigma_pred)
    p_lat = probability_map(m, grid, tau)
    d_gamma = p_pred >= gamma
    latent = p_lat >= gamma
    true_set = truth.reshape(-1) >= tau
    true_frac = float(true_set.double().mean())

    b_pred, a_pred = brier_and_auc(p_pred, truth, tau)
    b_lat, a_lat = brier_and_auc(p_lat, truth, tau)
    fi_pred = false_inclusion_rate(d_gamma, truth, tau)
    fi_lat = false_inclusion_rate(latent, truth, tau)
    vol_pred = float(d_gamma.double().mean())
    vol_lat = float(latent.double().mean())

    ev_pred = error_volumes(vol_pred, fi_pred, true_frac)
    ev_lat = error_volumes(vol_lat, fi_lat, true_frac)
    ap_pred, apm_pred, minority = _ap_pair(p_pred, truth, tau, true_frac)
    ap_lat, apm_lat, _ = _ap_pair(p_lat, truth, tau, true_frac)
    _, box_vol = inscribed_box_from_mask(grid, d_gamma, active=active, seed_score=p_pred)

    row = {
        "gamma": gamma, "tau": tau,
        "true_frac_above_tau": true_frac,
        "vol_pred": vol_pred, "vol_latent": vol_lat,
        # Erratum 5a: the two nan conditions are DIFFERENT and are never merged.
        # `fi` is nan when D_est is empty; `iou` is nan only when the UNION is empty, so
        # an empty D_est against a non-empty true set gives iou = 0, not nan.
        "empty_pred": vol_pred == 0.0,
        "empty_latent": vol_lat == 0.0,
        "empty_true": true_frac == 0.0,
        "empty_union_pred": vol_pred == 0.0 and true_frac == 0.0,
        "empty_union_latent": vol_lat == 0.0 and true_frac == 0.0,
        "iou_pred": iou(d_gamma, truth, tau), "iou_latent": iou(latent, truth, tau),
        "fi_pred": fi_pred, "fi_latent": fi_lat,
        "brier_pred": b_pred, "auc_pred": a_pred,
        "brier_latent": b_lat, "auc_latent": a_lat,
        # F2b. Read AP against its baseline, never against 0.5: a no-skill ranker scores
        # the prevalence, so AP is not comparable across cells whose prevalence runs from
        # 0.0012 to 0.999 unless the baseline travels with it.
        "auprc_pred": ap_pred, "auprc_minority_pred": apm_pred,
        "auprc_latent": ap_lat, "auprc_minority_latent": apm_lat,
        "ap_baseline": true_frac, "ap_baseline_minority": minority,
        "box_vol_pred": box_vol, "n_active": int(active.sum()),
    }
    for suffix, ev in (("pred", ev_pred), ("latent", ev_lat)):
        for k, v in ev.items():
            row[f"{k}_{suffix}"] = v
    return row


def score_campaign(rec, orc, grid, truth, active, taus) -> list[dict]:
    """Every (gamma, p) row for one regenerated campaign."""
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))
    # CHUNKED. model.posterior over the whole 20k grid builds the joint covariance and
    # costs 100.6s against 0.06s at 2k -- see boec.designspace.gp_adapter.
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, X):
            return mean, sd

    m = _M()
    # A lab does not know f, so the predictive SD is a PLUG-IN from the posterior mean.
    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    base = {**row_identity(rec.family, rec.dim, rec.sigma, rec.seed, rec.arm),
            "regret": rec.regret,
            "sup_err": sup_err(m, lambda X: truth, grid),
            "grid_r2": grid_r2(m, lambda X: truth, grid)}

    rows = []
    for t in taus:
        for gamma in GAMMAS:
            r = map_row(m, grid, truth, tau=t.tau, gamma=gamma,
                        sigma_pred=sigma_pred, active=active)
            # P5 measured this on the same grid and the same noiseless oracle. If the two
            # disagree the runner is not scoring the landscape P5 registered.
            if r["true_frac_above_tau"] != t.true_frac_above_tau:
                raise MissingGateTarget(
                    f"{rec.family} d={rec.dim} p={t.p}: prevalence re-measures "
                    f"{r['true_frac_above_tau']!r} against P5's committed "
                    f"{t.true_frac_above_tau!r}")
            rows.append({**base, "p": t.p, "tau_source": "results/p5-tau-quantile.json",
                         "tau_max": tau_max(gamma, rec.sigma),
                         "tau_above_ceiling": above_ceiling(t.tau, gamma, rec.sigma),
                         **r})
    del model, mean, sd
    gc.collect()
    return rows


# ======================================================================================
# RUNNER
# ======================================================================================
def _provenance(argv, elapsed: float) -> dict:
    import botorch, gpytorch, numpy, scipy                          # noqa: E401
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                         text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip())
    return {
        "git_sha": sha, "git_dirty": dirty,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "argv": argv, "elapsed_s": round(elapsed, 1),
        "python": platform.python_version(), "torch": torch.__version__,
        "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
        "numpy": numpy.__version__, "scipy": scipy.__version__,
        # Erratum 5c: recorded as documentation, not as a control variable. Exactness was
        # measured non-contingent on it; throughput is 3.6x and needs the SHELL prefix,
        # because BLAS reads OMP_NUM_THREADS at library load.
        "torch_num_threads": torch.get_num_threads(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=sorted(FAMILIES), required=True)
    ap.add_argument("--dim", type=int, default=6)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--arms", type=str, default=None, help="comma-separated; default all")
    ap.add_argument("--limit", type=int, default=None, help="seeds to score; default 25")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    out = Path(args.out) if args.out else OUT
    seeds = range(args.limit if args.limit else N_SEEDS)
    fam, dim, sigma = args.family, args.dim, args.sigma
    t0 = time.time()

    taus = [tau_for(fam, dim, p) for p in sorted(registered_p(fam, dim), reverse=True)]
    index, superseded, ungated = build_gate_index(fam, dim, sigma, arms)

    print(f"P6 · {fam} d={dim} sigma={sigma} · arms={arms}")
    print(f"  tau from {TAU_TABLE.relative_to(ROOT)}: "
          + "  ".join(f"p={t.p}->{t.tau:.5f}" for t in taus))
    print(f"  gamma={GAMMAS} (certification level ONLY; tau_q does not move with gamma)")
    print(f"  grid: {GRID_N} Sobol at seed {GRID_SEED} · threads={torch.get_num_threads()}")
    for arm, why in ungated.items():
        print(f"  UNGATABLE {arm}: {why}")
    n_dist = count_distinguishing(fam, dim, sigma)
    n_committed = sum(1 for k in index if k[0] == "doe")
    print(f"  doe gate distinguishes the pre-D20 column on {n_dist}/{n_committed} "
          f"committed seeds -- over the whole column, not just the seeds run here")
    # `tau_q` fixes tau by prevalence while `tau_max` falls with gamma, so unlike the
    # committed `tau_frac` grid (where tau = tau_frac * tau_max(gamma) shrank with it)
    # tau can now sit ABOVE the predictive ceiling. Those cells are empty because of the
    # noise floor and not because of the design, and the census is printed up front so
    # nobody spends a cell discovering it row by row.
    dead = [(t.p, g) for t in taus for g in GAMMAS if above_ceiling(t.tau, g, sigma)]
    print(f"  tau above the predictive ceiling in {len(dead)}/{len(taus)*len(GAMMAS)} "
          f"(p, gamma) cells -- empty by the noise floor, flagged per row")
    if dead:
        print("    " + "  ".join(f"p={p_}@g={g}" for p_, g in dead) + "\n")
    else:
        print()

    grid = sobol_grid(dim, GRID_N, seed=GRID_SEED)
    rows: list[dict] = json.loads(out.read_text())["rows"] if out.exists() else []
    have = {(r["family"], r["dim"], r["sigma"], r["seed"], r["arm"]) for r in rows}
    gate_fail: list[dict] = []

    for seed in seeds:
        for arm in arms:
            if (fam, dim, sigma, seed, arm) in have:
                continue
            t = time.time()
            rec = regenerate(fam, dim, sigma, seed, arm, family=fam)
            verdict = check_gate(rec, index, superseded, ungated)
            if verdict["gated"] and verdict["abs_delta"] != 0.0:
                gate_fail.append({**row_identity(fam, dim, sigma, seed, arm), **verdict})
                print(f"  !! GATE {arm} seed={seed} delta={verdict['abs_delta']:.3e}")

            orc = rec_oracle(rec, fam, dim, sigma, seed)
            with torch.no_grad():
                truth = orc.truth(grid).reshape(-1).double()
            active = torch.zeros(dim, dtype=torch.bool)
            if rec.kept_factors is None:
                active[:] = True
            else:
                active[list(rec.kept_factors)] = True

            scored = score_campaign(rec, orc, grid, truth, active, taus)
            for r in scored:
                r["gate"] = verdict
            rows.extend(scored)
            print(f"  [{seed:2d}] {arm:8s} regret={rec.regret:.4f} "
                  f"gated={verdict['gated']} ({time.time()-t:.1f}s)", flush=True)
            del truth
            gc.collect()

        out.write_text(json.dumps({
            "provenance": _provenance(sys.argv, time.time() - t0),
            "config": {"family": fam, "dim": dim, "sigma": sigma, "arms": list(arms),
                       "gammas": list(GAMMAS), "p_grid": [t.p for t in taus],
                       "grid_n": GRID_N, "grid_seed": GRID_SEED,
                       "tau_source": str(TAU_TABLE.relative_to(ROOT)),
                       "row_key": list(ROW_KEY),
                       "ungatable": ungated,
                       "doe_distinguishing_seeds": n_dist},
            "gate_failures": gate_fail, "rows": rows}, indent=1))

    print(f"\n{len(rows)} rows in {time.time()-t0:.0f}s · gate failures: {len(gate_fail)}")
    if gate_fail:
        print("*** REGISTERED KILL: a family arm missed its committed column by something "
              "other than 0. The family programme STOPS. Not a tolerance to widen. ***")
        sys.exit(1)


def rec_oracle(rec, family: str, dim: int, sigma: float, seed: int):
    """The same oracle the regeneration used, for the noiseless truth on the grid.

    A FRESH evaluator, as `replay.family_evaluator` builds one per call. `truth` draws no
    noise, so this cannot disturb the campaign's stream -- but it must be the same oracle,
    or the map is scored against a different landscape from the one that was searched.
    """
    from boec.replay import family_evaluator
    return family_evaluator(family, dim, sigma, seed)


if __name__ == "__main__":
    main()
