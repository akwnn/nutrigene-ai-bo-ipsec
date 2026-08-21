"""P2 — Version B on the gamma ladder, with the region metrics it has never had.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) under "PHASES 2-4
PRE-REGISTRATION", before this file existed.

------------------------------------------------------------------------------
THE GAP, MEASURED BY THE AUDIT AND NOT ASSERTED HERE
------------------------------------------------------------------------------

Version B's entire gamma coverage is **one point**, gamma = 0.50 (COVERAGE-MATRIX §3.1).
`run_versionb.py` computes ``theta = tau_frac * mu_max`` and carries no gamma constant at
all -- its own comment records that a ``GAMMA_FOR_AUC = 0.90`` was defined and never
used. Since ``tau_max(0.50, sigma) = 1.0`` exactly, its AUC column is **200/200 bitwise
identical** to `k6-designspace.json`'s gamma=0.50 row, so it is not independent evidence
either. gamma = 0.50 is also the only gamma at which the absolute tau is unconstrained by
the noise floor: the ladder is 1.0000 / 0.8689 / 0.7896 / 0.6796 / 0.5888 / 0.4184.

And it carries **no region metric that depends on gamma at all** (§3.2). The full absent
list is ``iou_pred``/``iou_latent``, ``sup_err``, ``grid_r2``, ``fi_pred``/``fi_latent``,
``vol_pred``, ``empty_pred``, ``box_vol_pred``, ``true_frac_above_tau``. By Amendment C2's
algebra the *latent* threshold is gamma-invariant, so AUC-against-truth genuinely does not
depend on gamma -- what depends on gamma is ``D_gamma`` and everything derived from it.
The ladder was therefore missing exactly where it would have bitten.

This runner closes both. Every metric is **imported** from :mod:`boec.designspace`,
:mod:`boec.norms` and :mod:`boec.vorobev`; nothing is reimplemented, because a second
copy of a scoring function is a second definition and could not be gated.

------------------------------------------------------------------------------
ONE GATE, AND THREE ARMS THAT ARE UNGATABLE IN PRINCIPLE
------------------------------------------------------------------------------

`plate1_only` is `lhs` at 48 wells, so it **is** gateable against
`results/k6-designspace-spread.json`. That gate is **full width**: every column the
committed rows carry, at every one of the 24 cells, at ``|delta| = 0.0``. Measured on a
pre-flight before this file was written, all 20 numeric columns -- including ``sup_err``,
``grid_r2``, ``iou_pred`` and ``box_vol_pred`` -- reproduced at exactly 0.0, so the gate
validates the whole scoring path and not merely the regret column.

`versionb`, `versionb_random` and `versionb_predictive` are **UNGATABLE IN PRINCIPLE**.
No comparator exists and none ever will: they are two-plate designs that no other runner
in this project builds. Their only guarantee is **seed determinism**, which is measured
against the committed Version B columns and reported in the ``determinism`` block --
labelled as reproduction by the same code path, which is not independent validation.
Every table that carries them must say so; :func:`gate_note` is that sentence.

**`plate1_only` may never be counted as a separate arm in a ranking** (D23.1). It is
`lhs`, to a worst |delta| of 4.44e-16. Both are reported; neither is double-counted.

------------------------------------------------------------------------------
THE ARITHMETIC TRAP THAT COSTS THE GATE
------------------------------------------------------------------------------

`run_versionb.py` scores `plate1_only` with a single ``scored_curve`` call and so misses
the committed `lhs` column by **4.44e-16**. That is not a discrepancy to be tolerated: it
is `run_e2.static_curve`'s 20-ordering mean, whose final values are all identical and
whose float64 average of 20 copies of x is not bitwise x. `boec.replay.regenerate`
reproduces that averaging deliberately, so `plate1_only` is built **through
``regenerate(..., "lhs")``**. The repair is to match the arithmetic; the bar stays 0.0.

------------------------------------------------------------------------------
THE REGISTERED KILL, WINNER NOT PRE-WRITTEN
------------------------------------------------------------------------------

`versionb` empirical containment is measured at **every** gamma x tau_frac x alpha cell
with :func:`boec.vorobev.empirical_containment` -- the non-circular one.
``containment_probability`` is what ``conservative_estimate`` *selects* on, so it cannot
fall below alpha and is kept only because it is already in the committed columns.

If containment falls below nominal at any cell, that is a **failure of the certificate**
and is reported as one. The committed 0.940 / 1.000 / 1.000 at gamma = 0.50 is not a
prediction for the ladder: gamma = 0.99 tightens ``tau_max`` from 1.0000 to 0.4184, which
lowers the threshold, enlarges both the true excursion set and the certified set, and
those two effects pull containment in opposite directions. A failure at high gamma is a
result, not a bug. It is reported as a fraction of **non-empty** certified sets, always
with its own ``n``, never averaged across cells with different ``n``.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch

from boec.designspace import (POSTERIOR_CHUNK, brier_and_auc, false_inclusion_rate,
                              gp_adapter, inscribed_box_from_mask, iou,
                              predictive_probability_map, probability_map, tau_max)
from boec.norms import grid_r2, sobol_grid, sup_err
from boec.replay import CampaignRecord, committed_rows, instance_by_id, regenerate, \
    scored_curve, unit_bounds
from boec.surrogate import build_gp
from boec.torch_oracle import BiphasicOracle
from boec.vorobev import (alpha_star, conservative_estimate, containment_probability,
                          empirical_containment, vorobev_deviation)

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "results" / "p2-versionb-gamma.json"

#: Read-only. The committed gate target for `plate1_only`, and the ONLY gate P2 has.
SPREAD = ROOT / "results" / "k6-designspace-spread.json"
#: Read-only. The committed Version B columns, used for the determinism block only.
VERSIONB = ROOT / "results" / "versionb.json"
VERSIONB_PRED = ROOT / "results" / "versionb-predictive.json"
#: Never written by anything. Overwriting either destroys the gate and the headline.
NEVER_OVERWRITE = (VERSIONB, VERSIONB_PRED, SPREAD,
                   ROOT / "results" / "k6-designspace.json")

#: K6's ladder, unchanged. `tau = tau_frac * tau_max(gamma, sigma_rel)`, never absolute.
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
#: Version B's joint-confidence sweep, unchanged.
ALPHAS = (0.50, 0.80, 0.95)
#: `versionb_predictive` runs LAST, as in `run_versionb.py`, so it cannot perturb the
#: arms above it -- the oracle noise stream is per-arm but the ordering is part of what
#: the committed columns reproduce.
ARMS = ("versionb", "versionb_random", "plate1_only", "versionb_predictive")
#: `run_versionb.py`'s mapping. Reported because every contrast here is at equal WELLS.
ROUNDS = {"versionb": 2, "versionb_random": 2, "versionb_predictive": 2,
          "plate1_only": 1}
_PLATE2_MODE = {"versionb": "lse", "versionb_random": "random",
                "versionb_predictive": "predictive"}

DIM, SIGMA, BUDGET = 6, 0.25, 48
GRID_N, SUBSET_N, N_DRAWS, GRID_SEED = 20_000, 2_000, 512, 0

#: The registration's stop condition 4 is "wanting to raise a tolerance". There is none.
GATE_TOL = 0.0
GATED_ARM = "plate1_only"
#: No comparator exists and none ever will. Seed determinism is their only guarantee.
UNGATABLE = ("versionb", "versionb_random", "versionb_predictive")
#: Every column `k6-designspace-spread.json` carries, minus the three that identify the
#: row. A gate that checks a hand-picked subset is not a gate (§3.6, P1's lesson).
GATED_COLUMNS = ("dim", "sigma", "regret", "sup_err", "grid_r2", "gamma", "tau_frac",
                 "tau", "tau_max", "true_frac_above_tau", "vol_pred", "vol_latent",
                 "empty_pred", "empty_latent", "iou_pred", "iou_latent", "fi_pred",
                 "fi_latent", "brier_pred", "auc_pred", "brier_latent", "auc_latent",
                 "box_vol_pred", "n_active")

#: `run_versionb.py`'s two-plate builder, imported rather than reimplemented. A second
#: copy of plate 2's LSE selection would be a second campaign, and its columns could not
#: be checked against the committed ones at all (D12).
_VB = importlib.util.module_from_spec(
    importlib.util.spec_from_file_location("_run_versionb",
                                           ROOT / "scripts" / "run_versionb.py"))
_VB.__spec__.loader.exec_module(_VB)


def gate_note() -> str:
    """The sentence every table carrying these arms must repeat."""
    return (f"{GATED_ARM} IS `lhs` at {BUDGET} wells and is gated full-width against "
            f"results/k6-designspace-spread.json at |delta| = {GATE_TOL}; it may never be "
            f"counted as a separate arm in a ranking (D23.1). "
            f"{', '.join(UNGATABLE)} are UNGATABLE IN PRINCIPLE -- no comparator exists "
            f"and none ever will -- and their only guarantee is seed determinism.")


def tau_for(gamma: float, tau_frac: float, sigma_rel: float) -> tuple[float, float]:
    """``(tau, tau_max)``, by `run_k6_designspace.py`'s arithmetic and no other."""
    tmax = tau_max(gamma, sigma_rel)
    return round(tau_frac * tmax, 10), tmax


# ------------------------------------------------------------------ committed columns


def _rows(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d if isinstance(d, list) else d["rows"]


def committed_lhs_index(path: Path = SPREAD) -> dict[tuple, dict]:
    """``(instance, seed, gamma, tau_frac) -> committed lhs row``.

    A comparator that is **absent raises**. `run_k6_designspace.py:181`'s
    ``if ref is not None`` skipped 100 campaigns in silence and nothing said so
    (COVERAGE-MATRIX §3.6); an empty index here is that defect, not a pass.
    """
    if not path.exists():
        raise SystemExit(f"{path} is the committed gate target and is missing; "
                         f"refusing to run {GATED_ARM} ungated")
    idx = {(r["instance"], r["seed"], r["gamma"], r["tau_frac"]): r
           for r in _rows(path) if r["arm"] == "lhs"}
    if not idx:
        raise SystemExit(f"{path} carries no `lhs` rows; {GATED_ARM} has no comparator "
                         f"and P2's only gate cannot run")
    return idx


def committed_versionb_index() -> dict[tuple[str, int, str], dict]:
    """``(instance, seed, arm) -> committed Version B row``, for the determinism block.

    NOT a gate. These rows were produced by the same code path this runner imports, so
    agreement proves the seed stream is reproducible and nothing more.
    """
    idx: dict[tuple[str, int, str], dict] = {}
    for path in (VERSIONB, VERSIONB_PRED):
        if not path.exists():
            continue
        for r in _rows(path):
            if r["arm"] in UNGATABLE:
                idx.setdefault((r["instance"], r["seed"], r["arm"]), r)
    return idx


def _delta(a, b) -> float:
    """``|a - b|``, with bools compared as bools and nan == nan."""
    if isinstance(a, bool) or isinstance(b, bool):
        return 0.0 if bool(a) == bool(b) else 1.0
    a, b = float(a), float(b)
    if math.isnan(a) and math.isnan(b):
        return 0.0
    return abs(a - b)


def gate_row(row: dict, ref: dict | None) -> list[dict]:
    """Every column of :data:`GATED_COLUMNS` at exactly :data:`GATE_TOL`."""
    if ref is None:
        raise SystemExit(f"no committed lhs row for {row['instance']} seed={row['seed']} "
                         f"gamma={row['gamma']} tau_frac={row['tau_frac']}")
    bad = []
    for k in GATED_COLUMNS:
        if k not in ref:
            raise SystemExit(f"committed lhs row has no column {k!r}; the gate cannot be "
                             f"full width and a partial gate is not a gate")
        d = _delta(row[k], ref[k])
        if d > GATE_TOL:
            bad.append({"column": k, "regenerated": row[k], "committed": ref[k],
                        "abs_delta": d})
    return bad


# ----------------------------------------------------------------------- the campaign


def plate1_only_record(instance: str, dim: int, sigma: float,
                       seed: int) -> CampaignRecord:
    """`plate1_only` is `lhs` at 48 wells, built by the arithmetic the column was.

    Via ``regenerate`` and not via ``static_design`` + ``scored_curve``: see the module
    docstring. The record comes back labelled `lhs`, which is what it is.
    """
    return regenerate(instance, dim, sigma, seed, "lhs")


def vorobev_columns(draws: torch.Tensor, truth_sub: torch.Tensor, tau: float,
                    alphas=ALPHAS) -> dict:
    """alpha*, the Vorob'ev deviation, and the conservative estimate at each alpha.

    ``ce_contain`` is **circular** -- ``conservative_estimate`` selects on it, so it
    cannot fall below alpha. It is kept because the committed Version B columns carry it
    and removing it would hide the tautology rather than expose it. ``ce_empirical`` is
    the real test, against known truth, and is ``nan`` for an empty set: vacuously
    contained, and counting that as a success would inflate the measured rate with
    campaigns that certified nothing.
    """
    out = {"alpha_star": alpha_star(draws, tau),
           "vorobev_deviation": vorobev_deviation(draws, tau)}
    for a in alphas:
        ce = conservative_estimate(draws, tau, a)
        n_ce = int(ce.sum())
        out[f"ce_vol_{a}"] = n_ce / ce.numel()
        out[f"ce_empty_{a}"] = n_ce == 0
        out[f"ce_contain_{a}"] = (containment_probability(draws, ce, tau)
                                  if n_ce else float("nan"))
        emp = empirical_containment(ce, truth_sub, tau)
        out[f"ce_empirical_{a}"] = float("nan") if emp is None else float(emp)
    return out


def score_campaign(*, X, Y, Yvar, orc, dim, grid, truth, X_sub, truth_sub, seed,
                   instance, arm, regret, gammas=GAMMAS, tau_fracs=TAU_FRACS,
                   alphas=ALPHAS, n_draws=N_DRAWS) -> list[dict]:
    """Every (gamma, tau_frac) row for one 48-well campaign.

    One GP, one chunked pass over the grid, one joint draw on the subset. The row shape
    is `run_k6_designspace.py`'s exactly -- that is what makes the `plate1_only` gate
    full width -- plus the Vorob'ev columns Version B already had.
    """
    model = build_gp(X, Y, Yvar, unit_bounds(dim))
    # CHUNKED. `model.posterior` over the whole 20k grid builds the JOINT covariance:
    # 0.06s at N=2,000 against 100.6s at N=20,000, and 3.2 GB of dense matrix whose
    # off-diagonal is never read. `gp_adapter` chunks at POSTERIOR_CHUNK = 2048.
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        """The grid mean/sd, already paid for. Only ever called with ``grid``."""

        def posterior_mean_and_sd(self, Z):
            return mean, sd

    m = _M()
    # A lab does not know f, so the predictive SD is a PLUG-IN from the posterior mean.
    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    # The joint draw, on the 2,000-point subset. `SUBSET_N < POSTERIOR_CHUNK`, so this
    # is the one place a joint covariance is wanted and it is small enough to want it.
    # Bit-for-bit `run_versionb._score`, so the committed columns are reproducible.
    with torch.no_grad():
        post = model.posterior(X_sub)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], n_draws, generator=g, dtype=torch.double)
        draws = (post.mean.reshape(-1, 1).double() + L @ z).T

    # Every arm here varies all d factors -- none screens -- so the active subspace is
    # the whole box. Amendment B3 does not bite, and pretending it might would pin an
    # axis that the design did vary.
    active = torch.ones(dim, dtype=torch.bool)

    base = {"instance": instance, "dim": dim, "sigma": orc.sigma_rel, "seed": seed,
            "arm": arm, "regret": regret, "n_wells": int(X.shape[0]),
            "rounds": ROUNDS[arm], "n_active": int(active.sum()),
            "sup_err": sup_err(m, lambda Z: truth, grid),
            "grid_r2": grid_r2(m, lambda Z: truth, grid),
            "gated": arm == GATED_ARM, "ungatable": arm in UNGATABLE}

    rows = []
    for gamma in gammas:
        for tf in tau_fracs:
            tau, tmax = tau_for(gamma, tf, orc.sigma_rel)
            p_pred = predictive_probability_map(m, grid, tau, sigma_pred)
            p_lat = probability_map(m, grid, tau)
            d_gamma = p_pred >= gamma
            latent = p_lat >= gamma
            true_set = truth.reshape(-1) >= tau

            b_pred, a_pred = brier_and_auc(p_pred, truth, tau)
            b_lat, a_lat = brier_and_auc(p_lat, truth, tau)
            _, box_vol = inscribed_box_from_mask(grid, d_gamma, active=active,
                                                 seed_score=p_pred)
            rows.append({**base, "gamma": gamma, "tau_frac": tf, "tau": tau,
                         "tau_max": tmax,
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
                         **vorobev_columns(draws, truth_sub, tau, alphas)})
    del model, mean, sd, draws
    gc.collect()
    return rows


def build_campaign(arm: str, instance: str, dim: int, sigma: float, seed: int,
                   orc_t) -> tuple:
    """``(X, Y, Yvar, regret)`` for one arm, by the arithmetic its column was built by.

    A **fresh** oracle per arm, because `orc.evaluate` consumes the noise stream and the
    committed Version B columns were produced with one oracle per arm. ``orc_t`` scores
    and is never evaluated against, so its stream stays untouched.
    """
    if arm == GATED_ARM:
        rec = plate1_only_record(instance, dim, sigma, seed)
        return rec.X, rec.Y, rec.Yvar, rec.regret
    inst = instance_by_id(instance, dim)
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    mu_max = float(inst.optimum_value)
    X, Y, V, _diag = _VB._two_plate(orc, dim, seed, mu_max, _PLATE2_MODE[arm])
    return X, Y, V, float(mu_max - scored_curve(orc_t, X, Y)[-1])


def synthetic_campaign(grid_n: int = 512, subset_n: int = 128, n_draws: int = 64,
                       seed: int = 0, dim: int = DIM, sigma: float = SIGMA) -> dict:
    """One real 48-well `lhs` campaign on a small grid. **SHAPE ONLY, never a result.**

    Used by the tests to assert the row carries every column and that the grid never
    goes through ``posterior`` in one call. A production row is 20,000 points.
    """
    instance = sorted({r["instance"] for r in committed_rows()
                       if r["dim"] == dim and r["sigma"] == sigma})[0]
    inst = instance_by_id(instance, dim)
    orc_t = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    grid = sobol_grid(dim, grid_n, seed=GRID_SEED)
    X_sub = sobol_grid(dim, subset_n, seed=GRID_SEED)
    with torch.no_grad():
        truth = orc_t.truth(grid).reshape(-1).double()
        truth_sub = orc_t.truth(X_sub).reshape(-1).double()
    X, Y, V, regret = build_campaign(GATED_ARM, instance, dim, sigma, seed, orc_t)
    return {"X": X, "Y": Y, "Yvar": V, "orc": orc_t, "dim": dim, "grid": grid,
            "truth": truth, "X_sub": X_sub, "truth_sub": truth_sub, "seed": seed,
            "instance": instance, "arm": GATED_ARM, "regret": regret,
            "n_draws": n_draws}


# -------------------------------------------------------------------------- the run


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
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "argv": list(argv), "python": platform.python_version(),
            "torch": torch.__version__, "botorch": botorch.__version__,
            "gpytorch": gpytorch.__version__, "numpy": numpy.__version__,
            "scipy": scipy.__version__}


def _config(dim: int, sigma: float, limit: int | None) -> dict:
    return {"dim": dim, "sigma": sigma, "budget": BUDGET, "arms": list(ARMS),
            "rounds": ROUNDS, "gammas": list(GAMMAS), "tau_fracs": list(TAU_FRACS),
            "alphas": list(ALPHAS), "grid_n": GRID_N, "subset_n": SUBSET_N,
            "grid_seed": GRID_SEED, "n_draws": N_DRAWS, "limit": limit,
            "posterior_chunk": POSTERIOR_CHUNK,
            "tau": "tau_frac * tau_max(gamma, sigma_rel), as run_k6_designspace.py",
            "gate": {"arm": GATED_ARM, "target": str(SPREAD.relative_to(ROOT)),
                     "target_arm": "lhs", "tol": GATE_TOL,
                     "columns": list(GATED_COLUMNS)},
            "ungatable": list(UNGATABLE), "note": gate_note()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=DIM)
    ap.add_argument("--sigma", type=float, default=SIGMA)
    ap.add_argument("--limit", type=int, default=None,
                    help="(instance, seed) pairs to score; default all 50")
    ap.add_argument("--arms", type=str, default=None,
                    help="comma-separated subset; default all four")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    out = args.out.resolve()
    for guarded in NEVER_OVERWRITE:
        if out == guarded.resolve():
            raise SystemExit(f"refusing to overwrite {guarded} -- it is a committed "
                             f"result. Pass a different --out.")
    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    unknown = set(arms) - set(ARMS)
    if unknown:
        raise SystemExit(f"unknown arms {sorted(unknown)}")

    prov = _provenance(sys.argv)
    gate_index = committed_lhs_index() if GATED_ARM in arms else {}
    det_index = committed_versionb_index()

    print(f"P2 · Version B on the gamma ladder · HEAD={prov['git_sha']}")
    print(f"cell d={args.dim} sigma={args.sigma} · arms={arms}")
    print(f"gamma={GAMMAS}\ntau_frac={TAU_FRACS} (of tau_max, never absolute) "
          f"· alpha={ALPHAS}")
    print(f"grid: {GRID_N} Sobol at seed {GRID_SEED} · draws: {N_DRAWS} on {SUBSET_N}")
    print(f"out={out.relative_to(ROOT)}")
    print(f"GATE: {gate_note()}\n")

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == args.dim and r["sigma"] == args.sigma
                   and r["arm"] == "qlogei"})
    if args.limit:
        keys = keys[:args.limit]
    print(f"{len(keys)} (instance, seed) pairs x {len(arms)} arms = "
          f"{len(keys) * len(arms)} campaigns x {len(GAMMAS) * len(TAU_FRACS)} cells\n")

    grid = sobol_grid(args.dim, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(args.dim, SUBSET_N, seed=GRID_SEED)
    rows: list[dict] = []
    gate_failures: list[dict] = []
    determinism: list[dict] = []
    n_gated = 0
    t0 = time.time()

    def _write() -> None:
        out.write_text(json.dumps({
            "provenance": prov,
            "config": _config(args.dim, args.sigma, args.limit),
            "gate": {"arm": GATED_ARM, "tol": GATE_TOL, "rows_checked": n_gated,
                     "columns": list(GATED_COLUMNS), "note": gate_note()},
            "gate_failures": gate_failures,
            "determinism": {
                "what_it_is": ("reproduction of the committed Version B columns by the "
                               "same code path. Seed determinism only -- NOT independent "
                               "validation, and not a gate."),
                "sources": [str(VERSIONB.relative_to(ROOT)),
                            str(VERSIONB_PRED.relative_to(ROOT))],
                "checks": determinism},
            "rows": rows}, indent=2))

    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, args.dim)
        orc_t = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
        with torch.no_grad():
            truth = orc_t.truth(grid).reshape(-1).double()
            truth_sub = orc_t.truth(X_sub).reshape(-1).double()

        for arm in arms:
            t = time.time()
            X, Y, V, regret = build_campaign(arm, inst_id, args.dim, args.sigma, seed,
                                             orc_t)
            scored = score_campaign(X=X, Y=Y, Yvar=V, orc=orc_t, dim=args.dim, grid=grid,
                                    truth=truth, X_sub=X_sub, truth_sub=truth_sub,
                                    seed=seed, instance=inst_id, arm=arm, regret=regret)

            if arm == GATED_ARM:
                for row in scored:
                    ref = gate_index.get((inst_id, seed, row["gamma"], row["tau_frac"]))
                    bad = gate_row(row, ref)
                    n_gated += 1
                    if bad:
                        gate_failures.append({"instance": inst_id, "seed": seed,
                                              "arm": arm, "gamma": row["gamma"],
                                              "tau_frac": row["tau_frac"],
                                              "failures": bad})
                if gate_failures:
                    _write()
                    print(f"\n*** GATE FAILURE {arm} {inst_id} seed={seed} ***")
                    for f in gate_failures[-1]["failures"][:8]:
                        print(f"    {f['column']}: {f['regenerated']!r} != committed "
                              f"{f['committed']!r} (delta {f['abs_delta']:.3e})")
                    raise SystemExit(
                        f"{GATED_ARM} missed its committed column by more than "
                        f"{GATE_TOL}. Stop condition 1. Not repaired, not absorbed.")
            elif (ref := det_index.get((inst_id, seed, arm))) is not None:
                determinism.append(_determinism_check(scored, ref, inst,
                                                      inst_id, seed, arm))

            rows.extend(scored)
            print(f"[{i:3d}/{len(keys)}] {arm:20s} {inst_id} seed={seed} "
                  f"n={int(X.shape[0])} regret={regret:.4f} "
                  f"a*={scored[0]['alpha_star']:.3f} "
                  f"{'GATED' if arm == GATED_ARM else 'ungatable'} "
                  f"({time.time() - t:.1f}s)", flush=True)

        _write()
        del truth, truth_sub
        gc.collect()

    _write()
    print(f"\n{len(rows)} scored rows in {time.time() - t0:.0f}s")
    print(f"{GATED_ARM} gate: {n_gated} row-comparisons x {len(GATED_COLUMNS)} columns, "
          f"{len(gate_failures)} failures")
    worst = max((c["worst_abs_delta"] for c in determinism), default=float("nan"))
    print(f"determinism (NOT a gate): {len(determinism)} campaigns checked against the "
          f"committed Version B columns, worst |delta| = {worst:.3e}")
    if gate_failures:
        sys.exit(1)


def _determinism_check(scored: list[dict], ref: dict, inst, inst_id: str, seed: int,
                       arm: str) -> dict:
    """Worst |delta| against the committed Version B row, per column.

    The committed columns were computed at ``theta = tau_frac * inst.optimum_value``
    while this runner uses ``tau_frac * tau_max(0.50, sigma) = tau_frac * 1.0``. Those
    coincide **bitwise** only where ``optimum_value`` is exactly 1.0, which it is for
    most but not all instances (§3.1's "1.0 +/- 2e-16 float offset"). ``exact_mu_max``
    records which case this campaign is, so the two are never pooled.
    """
    mu_max = float(inst.optimum_value)
    at_050 = {r["tau_frac"]: r for r in scored if r["gamma"] == 0.50}
    per_column: dict[str, float] = {"regret": _delta(scored[0]["regret"], ref["regret"])}
    for tf, row in at_050.items():
        pairs = {f"auc_{tf}": "auc_pred", f"brier_{tf}": "brier_pred",
                 f"alpha_star_{tf}": "alpha_star", f"vorobev_dev_{tf}": "vorobev_deviation"}
        for a in ALPHAS:
            for stem in ("ce_vol", "ce_empty", "ce_contain", "ce_empirical"):
                pairs[f"{stem}_{tf}_{a}"] = f"{stem}_{a}"
        for committed_key, ours in pairs.items():
            if committed_key in ref:
                per_column[ours] = max(per_column.get(ours, 0.0),
                                       _delta(row[ours], ref[committed_key]))
    return {"instance": inst_id, "seed": seed, "arm": arm,
            "optimum_value": mu_max, "exact_mu_max": mu_max == 1.0,
            "worst_abs_delta": max(per_column.values()),
            "per_column": per_column}


if __name__ == "__main__":
    main()
