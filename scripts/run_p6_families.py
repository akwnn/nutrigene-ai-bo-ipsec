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

#: **Registration Decision 2.** The order cells run in, and it is measured, not a guess.
#:
#: 1. ``(6, 0.25)`` -- the headline. Nothing displaces it.
#: 2. ``(6, 0.10)`` -- the sigma axis is the one with demonstrated sensitivity. D37 found
#:    `doe`'s regret advantage significant and beyond SESOI at (6, 0.25) ONLY, with the
#:    sign flipping to `qlognei` at both sigma=0.10 cells. `tau_max` also moves
#:    0.589 -> 0.836 there, so the entire emptiness structure changes -- which is what the
#:    ceiling census and the error volumes are about, so the degeneracy flags do their
#:    most interesting work in this cell. P3-B2's `tau_max_exact` sensitivity and P1's Q30
#:    sigma=0.10 comparator land in the same cell, making all three mutually checkable.
#: 3. ``(8, 0.25)`` -- demoted. P3's Kendall tau-b of each cell's six-arm regret ranking
#:    against the (6, 0.25) baseline: (6, 0.10) +0.47, **(8, 0.25) +0.60**, (8, 0.10)
#:    +0.33. The MOST concordant cell carries the LEAST new information.
#: 4. ``(8, 0.10)`` -- most divergent (+0.33) and therefore interesting, but it moves two
#:    axes at once and is only attributable once both single-axis cells exist.
#:
#: Stopping after 1 and 2 leaves a coherent pair -- the cross-family headline plus its
#: sigma sensitivity on the axis known to flip. Stopping after 1 and 3 would not.
CELL_ORDER = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
#: The only family that is a declared sensitivity rather than a headline.
SENSITIVITY_FAMILIES = ("ackley",)

#: **Erratum 6a.** These are properties of the CAMPAIGN, repeated verbatim across every
#: (gamma, p) row, so a row-wise count of them inflates by the number of cells -- 24x
#: here. "1200/1200" was quoted for a quantity that was 50/50. Emitted in the config so an
#: analyst cannot have to infer it.
CAMPAIGN_LEVEL_COLUMNS = ("regret", "grid_r2", "sup_err", "n_active", "gate")
#: Genuinely per-(gamma, p) and safe to count row-wise.
CELL_LEVEL_COLUMNS = ("tau", "tau_max", "tau_above_ceiling", "true_frac_above_tau",
                      "vol_pred", "vol_latent", "empty_pred", "empty_latent",
                      "empty_true", "empty_union_pred", "empty_union_latent",
                      "iou_pred", "iou_latent", "fi_pred", "fi_latent",
                      "brier_pred", "brier_latent", "auc_pred", "auc_latent",
                      "auprc_pred", "auprc_latent", "auprc_minority_pred",
                      "auprc_minority_latent", "ap_baseline", "ap_baseline_minority",
                      "type_I_vol_pred", "type_II_vol_pred", "total_error_vol_pred",
                      "intersect_pred", "implied_iou_pred", "box_vol_pred", "degenerate")
#: **Convention 1.** The scalar to rank on when one number is needed. NOT `type_I_vol`:
#: read alone it ranks SILENCE first, because an arm certifying the empty set scores
#: exactly 0. `doe` is 2nd of 8 on type I for that reason and no other, while being last
#: of 8 on type II, symmetric difference, IoU and Brier. Azzimonti & Ginsbourger report
#: both components; `total_error_vol` is their sum, the symmetric difference
#: |D_est \ D_true| + |D_true \ D_est|.
RANKING_SCALAR = "total_error_vol_pred"

#: **The F2a identity bound, PER POPULATION, both values named.** F2a's derivation
#: ``intersect / (vol + prevalence - intersect) == iou`` is exact in real arithmetic; what
#: differs is the float error measured on each committed population, and the registered
#: bound was measured on the optimiser arms only:
#:
#:   ``results/k6-designspace.json``         worst 2.220446049250313e-16 = 1.00 ULP
#:   ``results/k6-designspace-spread.json``  worst 3.3306690738754696e-16 = 1.50 ULP
#:
#: **P6 runs lhs, sobol and random**, so a gate asserting the 1-ULP bound would fail on
#: three of its six arms for a reason that is not an error. Neither value is widened into
#: a single global bar: each names the population it was measured on.
IOU_IDENTITY_BOUND = {
    "optimiser": 2.220446049250313e-16,   # k6-designspace.json: doe, qlogei, qlognei
    "spread": 3.3306690738754696e-16,     # k6-designspace-spread.json: lhs, sobol, random
}


#: The arms whose bound came from `k6-designspace-spread.json`.
SPREAD_POP = ("lhs", "sobol", "random")


def iou_bound_for(arm: str) -> float:
    """Which measured population this arm belongs to. Never a global bar."""
    return IOU_IDENTITY_BOUND["spread" if arm in ("lhs", "sobol", "random")
                              else "optimiser"]


#: **Lower-is-better or higher-is-better, per metric.** No cross-metric agreement check
#: may compare raw signs: Brier and regret and the error volumes are lower-is-better while
#: AUC, AUPRC, IoU and alpha* are higher-is-better, and comparing them unadjusted inverted
#: two of four readings in the F-analysis audit. Carried in the config so any table built
#: on these rows has it without having to know.
METRIC_DIRECTION = {
    "regret": "lower", "brier_pred": "lower", "brier_latent": "lower",
    "fi_pred": "lower", "fi_latent": "lower",
    "type_I_vol_pred": "lower", "type_II_vol_pred": "lower",
    "total_error_vol_pred": "lower", "sup_err": "lower",
    "type_I_vol_latent": "lower", "type_II_vol_latent": "lower",
    "total_error_vol_latent": "lower",
    "auc_pred": "higher", "auc_latent": "higher",
    "auprc_pred": "higher", "auprc_latent": "higher",
    "auprc_minority_pred": "higher", "auprc_minority_latent": "higher",
    "iou_pred": "higher", "iou_latent": "higher",
    "grid_r2": "higher", "box_vol_pred": "higher",
}

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

    # Convention 3: FLAG degenerate cells, never rank them. 6 of 24 cells in the hill
    # grid are ties because every region is empty in 100% of campaigns at tau_frac=0.95,
    # and on families this is worse, not better. A `nan` that gets averaged and a tie that
    # gets ranked are the two failure modes; naming the reason prevents both.
    degenerate = []
    if vol_pred == 0.0:
        degenerate.append("empty_pred")
    if true_frac == 0.0:
        degenerate.append("empty_true")
    if vol_pred == 0.0 and true_frac == 0.0:
        degenerate.append("empty_union_pred")
    if true_frac in (0.0, 1.0):
        degenerate.append("single_class")       # auc and auprc are undefined here

    row = {
        "gamma": gamma, "tau": tau,
        "true_frac_above_tau": true_frac,
        "degenerate": degenerate,
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
            # F2a's derivation is checkable, so it is checked rather than trusted, at the
            # bound measured on THIS arm's population.
            bound = iou_bound_for(rec.arm)
            for suffix in ("pred", "latent"):
                got, ref = r[f"implied_iou_{suffix}"], r[f"iou_{suffix}"]
                if got == got and ref == ref and abs(got - ref) > bound:
                    raise MissingGateTarget(
                        f"{rec.family} {rec.arm} seed={rec.seed} p={t.p} gamma={gamma}: "
                        f"error-volume identity misses iou_{suffix} by "
                        f"{abs(got - ref):.3e}, over the {bound:.3e} bound measured on "
                        f"the {'spread' if rec.arm in SPREAD_POP else 'optimiser'} arms")
            if r["true_frac_above_tau"] != t.true_frac_above_tau:
                raise MissingGateTarget(
                    f"{rec.family} d={rec.dim} p={t.p}: prevalence re-measures "
                    f"{r['true_frac_above_tau']!r} against P5's committed "
                    f"{t.true_frac_above_tau!r}")
            ceiling = above_ceiling(t.tau, gamma, rec.sigma)
            if ceiling:
                # Structurally empty by algebra, not by the design. Ranking an arm on a
                # cell it could not have won is not a comparison.
                r["degenerate"] = r["degenerate"] + ["above_ceiling"]
            rows.append({**base, "p": t.p, "tau_source": "results/p5-tau-quantile.json",
                         "tau_max": tau_max(gamma, rec.sigma),
                         "tau_above_ceiling": ceiling, **r})
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


CENSUS_OUT = ROOT / "results" / "p6-ceiling-census.json"


def ceiling_census() -> dict:
    """What fraction of each family's response range is certifiable at a given assurance.

    **A registered secondary result, not an artefact to route around.** Under `tau_q` the
    threshold is fixed by prevalence while `tau_max` still falls with gamma, so a cell can
    sit above the predictive ceiling and be empty by algebra. Which cells, and how many,
    is a design-space property of the family -- and this project has never reported it.

    **Counted at the (d, p) cell, never at the row.** Hill carries 25 instances per
    (d, p) and the four external families carry one landscape each, so a raw row count
    gives hill 25x the weight and makes it look like an outlier when it is not. That is
    Erratum 6a's failure mode -- counting a per-campaign property per row -- in a new
    place. `hill_unanimous` records whether the 25 instances agree, which is what licenses
    collapsing them to one cell.

    gamma = 0.50 is clean everywhere BY CONSTRUCTION and the census shows it as such:
    z(0.50) = 0, so `tau_max(0.50, sigma) = mu_max = 1.0` exactly, `UnitScaled` puts every
    family's optimum at 1, and the largest `tau_q` in the registered grid is 0.98631.
    """
    table = json.loads(TAU_TABLE.read_text())["rows"]
    cells: dict[tuple, list[float]] = {}
    for r in table:
        cells.setdefault((r["family"], r["dim"], r["p"]), []).append(r["tau_q"])

    rows, summary = [], {}
    for sigma in (0.25, 0.10):
        for gamma in GAMMAS:
            tmax = tau_max(gamma, sigma)
            for (family, dim, p), taus in sorted(cells.items()):
                n_above = sum(1 for t in taus if t > tmax)
                above = n_above * 2 > len(taus)
                rows.append({
                    "family": family, "dim": dim, "p": p, "gamma": gamma,
                    "sigma": sigma, "tau_max": tmax,
                    "tau_q_min": min(taus), "tau_q_max": max(taus),
                    "n_landscapes": len(taus), "n_landscapes_above": n_above,
                    "unanimous": n_above in (0, len(taus)),
                    "above_ceiling": above,
                })
                k = (family, sigma, gamma)
                s_ = summary.setdefault(f"{family}|sigma={sigma}|gamma={gamma}",
                                        {"cells": 0, "above": 0})
                s_["cells"] += 1
                s_["above"] += int(above)
    for v in summary.values():
        v["rate"] = v["above"] / v["cells"]
    return {"rows": rows, "summary": summary}


def write_census() -> None:
    doc = ceiling_census()
    doc["provenance"] = _provenance(sys.argv, 0.0)
    doc["config"] = {
        "unit": "(family, dim, p) cell -- NOT the row. Hill has 25 landscapes per cell "
                "and each external family has 1, so a row count weights hill 25x.",
        "tau_source": str(TAU_TABLE.relative_to(ROOT)),
        "gammas": list(GAMMAS), "sigmas": [0.25, 0.10],
    }
    CENSUS_OUT.write_text(json.dumps(doc, indent=1))

    n_dis = sum(1 for r in doc["rows"] if not r["unanimous"])
    print(f"ceiling census -> {CENSUS_OUT.relative_to(ROOT)} · {len(doc['rows'])} cells · "
          f"{n_dis} with landscapes disagreeing inside a cell")
    for sigma in (0.25, 0.10):
        print(f"\n  sigma={sigma}   " + "  ".join(f"g={g:<5}" for g in GAMMAS))
        for family in ("rosenbrock", "levy", "hill", "hartmann6", "ackley"):
            cells = [summ for g in GAMMAS
                     for k, summ in doc["summary"].items()
                     if k == f"{family}|sigma={sigma}|gamma={g}"]
            print(f"  {family:11s} " + "  ".join(
                f"{c['above']}/{c['cells']}    " for c in cells))


def ckpt_path(family: str, dim: int, sigma: float) -> Path:
    """One append-only checkpoint per (family, dim, sigma). One JSON line per campaign.

    **This box SIGKILLs workers.** Three runs have died with `BrokenProcessPool` --
    workers not raising, being *killed* -- and one lost 8 completed campaigns. So a
    finished campaign is on disk before the next one starts, and
    `results/p6-families.json` is written **once, whole, by `--merge`**. A half-finished
    run therefore cannot be mistaken for a finished result: the result file does not exist
    until someone merges.
    """
    return ROOT / "results" / f"p6-{family}-d{dim}-s{sigma:g}.ckpt.jsonl"


def read_checkpoint(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def merge() -> None:
    """Assemble every checkpoint into `results/p6-families.json`, once, whole."""
    entries, files = [], sorted((ROOT / "results").glob("p6-*.ckpt.jsonl"))
    for f in files:
        entries.extend(read_checkpoint(f))
    rows = [r for e in entries for r in e["rows"]]
    if not rows:
        sys.exit("no checkpoints to merge")

    if OUT.exists():
        existing = len(json.loads(OUT.read_text())["rows"])
        if len(rows) < existing:
            # A merge is a pure function of the checkpoints, so a SHRINKING merge means
            # checkpoints were deleted. Never silently replace a larger committed result.
            sys.exit(f"refusing to shrink {OUT.name}: {existing} committed rows, "
                     f"{len(rows)} in the checkpoints")

    cells = sorted({(e["family"], e["dim"], e["sigma"]) for e in entries})
    OUT.write_text(json.dumps({
        "provenance": _provenance(sys.argv, 0.0),
        "config": {"gammas": list(GAMMAS), "grid_n": GRID_N, "grid_seed": GRID_SEED,
                   "tau_source": str(TAU_TABLE.relative_to(ROOT)),
                   "row_key": list(ROW_KEY),
                   "ranking_scalar": RANKING_SCALAR,
                   "ranking_note": "type_I_vol read alone ranks SILENCE first -- an arm "
                                   "certifying the empty set scores exactly 0. Rank on "
                                   "the symmetric difference; report both components.",
                   "iou_identity_bound": IOU_IDENTITY_BOUND,
                   "iou_identity_note": "measured per population: 1.00 ULP on the "
                                        "optimiser arms (k6-designspace.json), 1.50 ULP "
                                        "on the spread arms "
                                        "(k6-designspace-spread.json). Never widened "
                                        "into one global bar.",
                   "metric_direction": METRIC_DIRECTION,
                   "direction_note": "no cross-metric agreement check may compare raw "
                                     "signs; Brier and the error volumes are "
                                     "lower-is-better, AUC and IoU are higher-is-better.",
                   "campaign_level_columns": list(CAMPAIGN_LEVEL_COLUMNS),
                   "cell_level_columns": list(CELL_LEVEL_COLUMNS),
                   "counting_note": "Erratum 6a: campaign_level_columns repeat across "
                                    "every (gamma, p) row; counting them row-wise "
                                    "inflates by the number of cells.",
                   "degenerate_note": "Rows with a non-empty `degenerate` list are "
                                      "FLAGGED, not ranked. Never average a nan; never "
                                      "rank a tie.",
                   "cells": [list(c) for c in cells],
                   "checkpoints": [f.name for f in files]},
        "gate_failures": [g for e in entries for g in e.get("gate_failures", [])],
        "rows": rows}, indent=1))
    print(f"merged {len(files)} checkpoints · {len(entries)} campaigns · {len(rows)} rows "
          f"· {len(cells)} cells -> {OUT.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=sorted(FAMILIES))
    ap.add_argument("--dim", type=int, default=6)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--arms", type=str, default=None, help="comma-separated; default all")
    ap.add_argument("--limit", type=int, default=None, help="seeds to score; default 25")
    ap.add_argument("--merge", action="store_true",
                    help="assemble every checkpoint into results/p6-families.json")
    ap.add_argument("--census", action="store_true",
                    help="write the ceiling census; zero compute, reads the tau table")
    ap.add_argument("--ckpt", type=str, default=None, help="override checkpoint path")
    args = ap.parse_args()

    if args.census:
        return write_census()
    if args.merge:
        return merge()
    if not args.family:
        ap.error("--family is required unless --merge")

    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    seeds = range(args.limit if args.limit else N_SEEDS)
    fam, dim, sigma = args.family, args.dim, args.sigma
    ckpt = Path(args.ckpt) if args.ckpt else ckpt_path(fam, dim, sigma)
    t0 = time.time()

    taus = [tau_for(fam, dim, p) for p in sorted(registered_p(fam, dim), reverse=True)]
    index, superseded, ungated = build_gate_index(fam, dim, sigma, arms)

    print(f"P6 · {fam} d={dim} sigma={sigma} · arms={arms}")
    print(f"  tau from {TAU_TABLE.relative_to(ROOT)}: "
          + "  ".join(f"p={t.p}->{t.tau:.5f}" for t in taus))
    print(f"  gamma={GAMMAS} (certification level ONLY; tau_q does not move with gamma)")
    print(f"  grid: {GRID_N} Sobol at seed {GRID_SEED} · threads={torch.get_num_threads()}"
          f" · OMP={os.environ.get('OMP_NUM_THREADS')}")
    print(f"  ranking scalar: {RANKING_SCALAR} (symmetric difference; NOT type I alone)")
    for arm, why in ungated.items():
        print(f"  UNGATABLE {arm}: {why}")
    n_dist = count_distinguishing(fam, dim, sigma)
    n_committed = sum(1 for k in index if k[0] == "doe")
    print(f"  doe gate distinguishes the pre-D20 column on {n_dist}/{n_committed} "
          f"committed seeds -- over the whole column, not just the seeds run here")
    dead = [(t.p, g) for t in taus for g in GAMMAS if above_ceiling(t.tau, g, sigma)]
    print(f"  tau above the predictive ceiling in {len(dead)}/{len(taus)*len(GAMMAS)} "
          f"(p, gamma) cells -- empty by the noise floor, flagged per row")
    if dead:
        print("    " + "  ".join(f"p={p_}@g={g}" for p_, g in dead))

    grid = sobol_grid(dim, GRID_N, seed=GRID_SEED)
    done = read_checkpoint(ckpt)
    have = {tuple(e["key"]) for e in done}
    print(f"  checkpoint {ckpt.name}: {len(done)} campaigns already done\n", flush=True)

    for seed in seeds:
        for arm in arms:
            key = (fam, dim, sigma, seed, arm)
            if key in have:
                continue
            t = time.time()
            rec = regenerate(fam, dim, sigma, seed, arm, family=fam)
            verdict = check_gate(rec, index, superseded, ungated)
            failures = []
            if verdict["gated"] and verdict["abs_delta"] != 0.0:
                failures.append({**row_identity(fam, dim, sigma, seed, arm), **verdict})
                print(f"  !! GATE {arm} seed={seed} delta={verdict['abs_delta']:.3e}",
                      flush=True)

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
            # ON DISK BEFORE THE NEXT CAMPAIGN STARTS. A SIGKILL here loses one campaign.
            with ckpt.open("a") as fh:
                fh.write(json.dumps({"key": list(key), "family": fam, "dim": dim,
                                     "sigma": sigma, "seed": seed, "arm": arm,
                                     "gate_failures": failures, "rows": scored}) + "\n")
            print(f"  [{seed:2d}] {arm:8s} regret={rec.regret:.4f} "
                  f"gated={verdict['gated']} ({time.time()-t:.1f}s)", flush=True)
            del truth
            gc.collect()

            if failures:
                print("*** REGISTERED KILL: a family arm missed its committed column by "
                      "something other than 0. The family programme STOPS. This is not a "
                      "tolerance to widen. ***", flush=True)
                sys.exit(1)

    total = len(read_checkpoint(ckpt))
    print(f"\n{total} campaigns in {ckpt.name} · {time.time()-t0:.0f}s · gate failures: 0")
    print(f"  results/p6-families.json is NOT written here. Run --merge when cells finish.")


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
