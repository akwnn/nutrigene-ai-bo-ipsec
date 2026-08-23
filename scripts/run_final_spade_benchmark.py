"""The prospective confirmatory benchmark for `spade-final-2026-08-23`.

    .venv/bin/python scripts/run_final_spade_benchmark.py --condition C1 --limit 100

Writes ``results/final-spade-primary.json`` (or ``--out``), checkpointing to a sibling
``.ckpt.jsonl`` so a killed run resumes instead of restarting.

------------------------------------------------------------------------------
WHAT MAKES THIS RUN DIFFERENT FROM EVERY OTHER RUNNER IN THIS REPOSITORY
------------------------------------------------------------------------------

It is **prospective**. FINDINGS §43.5 states the gap plainly: *"Version C has never been run
as a method. Every number is Version B's wells scored under Version C's rules."* Every
committed SPADE certificate figure in this project is a **re-score** of wells that were
already chosen.

A re-score cannot test an **allocation** rule, because the allocation already happened. The
`m0` / `m4` / `m8` question -- does spending part of plate 2 locally buy regret without
costing the certificate -- is answerable **only** by generating fresh campaigns whose plate-2
batch is chosen live from a live plate-1 fit. That is what this file does, and it is the
entire reason the study exists.

------------------------------------------------------------------------------
THE CERTIFICATE IS CROSS-FIT, AND THE CIRCULAR COLUMN IS KEPT BESIDE IT
------------------------------------------------------------------------------

``conservative_columns`` emits ``ce_split_contain_{alpha}`` (selected on one half of the
draws, scored on the other) as the **primary** number, ``ce_contain_{alpha}`` (the circular
one ``conservative_estimate`` selects on, which cannot fall below alpha) as a labelled
**diagnostic**, and their difference as ``ce_selection_bias_{alpha}``.

Keeping the circular column is not clutter. §29.3 measured the selection bias at 1.5-3.5
points at 4,096 draws, concentrated exactly where the Vorob'ev quantiles tie, and the only
way that stays visible in the final tables is if both columns ride on every row. Removing
the tautology would hide it rather than expose it.

``N_DRAWS_HALF = 2048`` per half, 4,096 total. §29 measured §14's four sub-nominal cells
climbing from 0.860 to 0.980 between 512 and 1,024 draws and flattening: **512 is not enough
to estimate ``CE_alpha``'s containment at gamma >= 0.95**, and this project reported a
draw-count artefact as a property of SPADE for a week before F3 found it.

------------------------------------------------------------------------------
BOTH TERMINAL RULES, ON EVERY ARM, ALWAYS
------------------------------------------------------------------------------

Rule A is the observed-data pick; rule P is ``optimum - truth(argmax posterior mean)``,
located by ``grid_screened_argmax`` on the registered 20,000-point Sobol grid then
``constrained_argmax``. Both are computed for **every** arm on **every** campaign.

§43.1 records what happens otherwise: K-C1's bar compared a rule-A column against a rule-P
number, and like-for-like the gap fell inside SESOI -- the claim became *parity, not a win*.
Emitting both columns unconditionally is what makes that mistake impossible downstream
rather than merely discouraged.
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.calibration import murphy_decomposition                    # noqa: E402
from boec.designspace import (brier_and_auc, gp_adapter, iou,        # noqa: E402
                              false_inclusion_rate,
                              predictive_probability_map)
from boec.final_spade import ROW_SCHEMA, spade_plate2                # noqa: E402
from boec.lse import exclusion_radius                                # noqa: E402
from boec.metrics import grid_screened_argmax                        # noqa: E402
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import (family_evaluator, instance_by_id,           # noqa: E402
                         regenerate, scored_curve, unit_bounds)
from boec.runner import static_design                                # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402
from boec.versionc import (ard_lengthscales, conservative_columns,   # noqa: E402
                           n_effective, split_joint_draws)

OUT_DEFAULT = ROOT / "results" / "final-spade-primary.json"
FEASIBILITY = ROOT / "results" / "final-spade-feasibility.json"
P2_COMMITTED = ROOT / "results" / "p2-versionb-gamma.json"

STUDY_ID = "spade-final-2026-08-23"
REGISTRATION_COMMIT = "c4f58d3"

N_PLATE1, N_PLATE2, BUDGET = 40, 8, 48
CAND_N = 4096
#: 🔴 ERRATUM 1. Plate 2's LSE criterion targets ONE threshold; scoring still spans both.
#: `tau_q` at p=0.25 is the moderate target, mirroring the original `DESIGN_TAU_FRAC=0.75`
#: arrangement. An arm that re-planned its boundary batch per scoring threshold would be a
#: different arm at each one, and the contrast would not be between designs.
DESIGN_TAU_Q = 0.25
GRID_N, SUBSET_N, GRID_SEED = 20_000, 2_000, 0
#: 2048 PER HALF -- 4,096 total. See the module docstring; 512 is a known artefact.
N_DRAWS_HALF = 2048
TAU_QS = (0.10, 0.25)
TAU_TABLE = ROOT / "results" / "p5-tau-quantile.json"
#: 🔴 ERRATUM 1. gamma=0.95 is PRIMARY only at sigma=0.10; at sigma=0.25 the 0.95 ceiling
#: sits at prevalence ~0.71 on hill, so it would test the ceiling and not the method.
GAMMAS = (0.50, 0.95, 0.99)
ALPHAS = (0.80, 0.95)
N_RESTARTS, RAW_SAMPLES, LOCATOR_SEED = 10, 512, 0

#: Spec §4. `mandatory` arms block a primary conclusion by their absence (§13.6); a missing
#: one is recorded with an `unavailable_reason` and never silently dropped.
ARMS: dict[str, dict] = {
    "spade_cf_m0":         {"fam": "SPADE",        "rounds": 2, "m": 0,    "wells": 48},
    "spade_cf_m4":         {"fam": "SPADE",        "rounds": 2, "m": 4,    "wells": 48},
    "spade_cf_m8":         {"fam": "SPADE",        "rounds": 2, "m": 8,    "wells": 48},
    "spade_plate1_only":   {"fam": "SPADE-ctrl",   "rounds": 1, "m": None, "wells": 40},
    "spade_random_plate2": {"fam": "SPADE-ctrl",   "rounds": 2, "m": None, "wells": 48},
    "sobol":               {"fam": "space-filling", "rounds": 1, "m": None, "wells": 48},
    "lhs":                 {"fam": "space-filling", "rounds": 1, "m": None, "wells": 48},
    "random":              {"fam": "space-filling", "rounds": 1, "m": None, "wells": 48},
    "qlognei":             {"fam": "BO",           "rounds": 10, "m": None, "wells": 48},
    "qlogei":              {"fam": "BO",           "rounds": 10, "m": None, "wells": 48},
    "doe":                 {"fam": "classical",    "rounds": 3, "m": None, "wells": 48},
}


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def _dirty() -> bool:
    return bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                               text=True).stdout.strip())


def conditions() -> dict[str, dict]:
    """Read the condition matrix and its regime classes from the COMMITTED feasibility
    artefact. Never re-derived here: a runner that recomputed the class could disagree
    with the gate, and the class must be the one frozen before campaigns."""
    if not FEASIBILITY.exists():
        raise SystemExit(
            f"{FEASIBILITY} is missing. The feasibility gate must be committed BEFORE any "
            "campaign runs (spec §6.2 / §19 step 5). Run "
            "scripts/run_final_spade_feasibility.py first.")
    d = json.loads(FEASIBILITY.read_text())
    out: dict[str, dict] = {}
    for r in d["rows"]:
        out.setdefault(r["condition_id"], {
            "family": r["family"], "dim": r["dimension"], "sigma": r["sigma"],
            "tier": r["tier"], "mu_max": r["mu_max"], "by_tau": {}})
        out[r["condition_id"]]["by_tau"][r["tau_q_p"]] = {
            "tau_raw": r["tau_raw"], "regime_class": r["regime_class"],
            "gammas_primary": r["gammas_primary"],
            "above_ceiling": r["above_ceiling"], "true_prevalence": r["true_prevalence"],
            "tau_max_by_gamma": r["tau_max_by_gamma"]}
    return out


def _keys(family: str, n: int) -> list[tuple]:
    if family == "hill":
        ks = sorted({(r["instance"], r["seed"]) for r in
                     json.loads(P2_COMMITTED.read_text())["rows"]})
        return ks[:n]
    return [(family, s) for s in range(n)]


def _oracle(family: str, instance: str, dim: int, sigma: float, seed: int):
    if family == "hill":
        return BiphasicOracle(instance_by_id(instance, dim), sigma_rel=sigma, seed=seed)
    return family_evaluator(family, dim, sigma, seed)


def spade_builder(m: int | None, mode: str, design_theta: float):
    """``builder(orc, dim, seed) -> (X, Y, Yvar, kept, held)`` for one SPADE arm.

    ``mode`` is ``"lse"`` (the m-allocation arms), ``"random"`` (the causal control) or
    ``"plate1"`` (no plate 2 at all).

    The plate-1 design, the candidate set and the GP are **identical** across all three, so
    the arms differ in exactly the registered quantity and nothing else.
    """
    def builder(orc, dim: int, seed: int):
        bounds = unit_bounds(dim)
        X1 = static_design(bounds, "lhs", N_PLATE1, seed)
        Y1, V1 = orc.evaluate(X1)
        if mode == "plate1":
            return X1, Y1, V1, None, None

        model = build_gp(X1, Y1, V1, bounds)
        if mode == "random":
            g = torch.Generator().manual_seed(10_000 + seed)
            X2 = torch.rand(N_PLATE2, dim, generator=g, dtype=torch.double)
        else:
            cand = sobol_grid(dim, CAND_N, seed=seed)
            ad = gp_adapter(model)
            X2, _diag = spade_plate2(ad, cand, X1, design_theta, N_PLATE2,
                                     int(m), ard_lengthscales(model),
                                     exclude=exclusion_radius(model))
        Y2, V2 = orc.evaluate(X2)
        del model
        gc.collect()
        return (torch.cat([X1, X2]), torch.cat([Y1, Y2]), torch.cat([V1, V2]), None, None)

    return builder


def build(cond: dict, instance: str, arm: str, seed: int):
    """One campaign. SPADE arms go through the builder hook; everything else through
    ``replay``'s own dispatch, so the baselines are generated by the code that produced
    every committed baseline column in this project."""
    family, dim, sigma = cond["family"], cond["dim"], cond["sigma"]
    fam_kw = {} if family == "hill" else {"family": family}
    spec = ARMS[arm]

    if arm.startswith("spade_"):
        mode = ("plate1" if arm == "spade_plate1_only"
                else "random" if arm == "spade_random_plate2" else "lse")
        return regenerate(instance, dim, sigma, seed, arm,
                          builder=spade_builder(spec["m"], mode,
                                                float(cond["by_tau"][DESIGN_TAU_Q]["tau_raw"])),
                          **fam_kw)
    return regenerate(instance, dim, sigma, seed, arm, **fam_kw)


def score(cond: dict, instance: str, arm: str, seed: int, grid, X_sub, truth,
          truth_sub, regime_by_tau: dict, head: str) -> list[dict]:
    """Every ``(tau_frac, gamma, alpha)`` row for one campaign."""
    family, dim, sigma = cond["family"], cond["dim"], cond["sigma"]
    mu_max = cond["mu_max"]
    bounds = unit_bounds(dim)
    spec = ARMS[arm]

    orc_t = _oracle(family, instance, dim, sigma, seed)   # scoring oracle, own stream
    rec = build(cond, instance, arm, seed)
    model = build_gp(rec.X, rec.Y, rec.Yvar, bounds)
    ad = gp_adapter(model)

    # --- rule A and rule P, both, for every arm (spec §7.4) -----------------------
    regret_a = float(rec.regret)

    def predict(Z, _m=model):
        with torch.no_grad():
            return _m.posterior(Z).mean

    grid_mean, grid_sd = ad.posterior_mean_and_sd(grid)
    r = grid_screened_argmax(predict, grid, grid_mean, bounds, n_restarts=N_RESTARTS,
                             raw_samples=RAW_SAMPLES, seed=LOCATOR_SEED)
    with torch.no_grad():
        regret_p = float(mu_max - orc_t.truth(r.x.reshape(1, -1)))
        oracle_best = float(mu_max - truth.max())
    n_eff = n_effective(rec.X, r.x.reshape(-1), ard_lengthscales(model))

    # --- the joint draws, split, drawn SEQUENTIALLY (versionc's requirement) ------
    draws_sel, draws_val = split_joint_draws(model, X_sub, n_draws=N_DRAWS_HALF, seed=seed)

    sigma_pred = ((sigma * grid_mean).abs() ** 2 + float(orc_t.sigma_add) ** 2).sqrt()

    class _M:
        def posterior_mean_and_sd(self, Z):
            return grid_mean, grid_sd

    rows: list[dict] = []
    for p_q in TAU_QS:
        reg = regime_by_tau.get(p_q, {})
        theta = float(reg["tau_raw"])      # the COMMITTED tau_q, never recomputed
        cols = conservative_columns(draws_sel, draws_val, truth_sub, theta, alphas=ALPHAS)

        p = predictive_probability_map(_M(), grid, theta, sigma_pred)
        brier, auc = brier_and_auc(p, truth, theta)
        murphy = murphy_decomposition(p, truth, theta)
        fi = false_inclusion_rate(p >= 0.5, truth, theta)
        prevalence = float((truth >= theta).double().mean())
        vol = float((p >= 0.5).double().mean())
        # Symmetric difference = type I + type II, the PRIMARY map scalar. Type I alone
        # ranks silence first (§9.4) and is never emitted without its partner.
        #
        # 🔴 An earlier revision of this block computed the volumes by hand and left a
        # dead line that assigned `type_i` twice. `error_volumes` is the REGISTERED
        # derivation (Azzimonti & Ginsbourger 2018), it is validated against the committed
        # `iou_pred` column in `tests/test_calibration.py`, and it is what
        # `conservative_columns` already uses for the certificate. Two derivations of one
        # quantity in one runner is exactly the "two sources of truth" defect §9.5 and §14
        # punished this project for.
        ev = error_volumes(vol, fi, prevalence)
        type_i = ev["type_I_vol"]
        type_ii = ev["type_II_vol"]

        for gamma in GAMMAS:
            for alpha in ALPHAS:
                rows.append({
                    "study_id": STUDY_ID, "registration_commit": REGISTRATION_COMMIT,
                    "code_commit": head, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "git_hash": head,
                    "environment_fingerprint": f"py{platform.python_version()}"
                                               f"/torch{torch.__version__}",
                    "family": family, "dimension": dim, "sigma": sigma,
                    "instance_seed": instance, "campaign_seed": seed,
                    "noise_stream_seed": f"{family}|{dim}|{sigma}|{instance}|{seed}",
                    "regime_class": reg.get("regime_class"),
                    "arm": arm, "arm_family": spec["fam"],
                    "total_wells": int(rec.X.shape[0]),
                    "plate1_wells": N_PLATE1 if arm.startswith("spade_") else None,
                    "plate2_wells": (0 if arm == "spade_plate1_only"
                                     else N_PLATE2 if arm.startswith("spade_") else None),
                    "confirmation_wells": 0, "rounds": spec["rounds"],
                    "adaptive_decisions": spec["rounds"] - 1,
                    "model_fits": spec["rounds"], "m_local": spec["m"],
                    "m_local_short": None, "n_effective": n_eff,
                    "terminal_rule": "both", "gamma": gamma, "alpha": alpha,
                    "tau_definition": "tau_q -- per-family prevalence quantile (Erratum 1)",
                    "tau_raw": theta, "tau_frac_or_quantile": p_q,
                    "tau_max": reg.get("tau_max_by_gamma", {}).get(str(gamma)),
                    "above_ceiling": reg.get("above_ceiling"),
                    "true_prevalence": prevalence,
                    "rankable": True,
                    "empty_predictive_region": bool(vol == 0.0),
                    "nonempty_certificate": not bool(cols[f"ce_empty_{alpha}"]),
                    "posterior_draws": 2 * N_DRAWS_HALF,
                    "selection_draws": N_DRAWS_HALF, "evaluation_draws": N_DRAWS_HALF,
                    "draw_split_seed": seed,
                    "selected_quantile": None, "candidate_quantile_count": 64,
                    # PRIMARY: cross-fit. DIAGNOSTIC: same-draw. Both, always (§29.3).
                    "crossfit_containment": cols[f"ce_split_contain_{alpha}"],
                    "same_draw_containment": cols[f"ce_contain_{alpha}"],
                    "empirical_containment": cols[f"ce_empirical_{alpha}"],
                    "certificate_volume": cols[f"ce_vol_{alpha}"],
                    "regret_rule_a": regret_a, "regret_rule_p": regret_p,
                    "oracle_best_regret": oracle_best,
                    "identification_gap_rule_a": regret_a - oracle_best,
                    "identification_gap_rule_p": regret_p - oracle_best,
                    "symmetric_difference_pred": type_i + type_ii,
                    "type_i_volume_pred": type_i, "type_ii_volume_pred": type_ii,
                    "brier": brier, "auc_pred": auc,
                    "murphy_calibration": murphy.get("calibration"),
                    "murphy_refinement": murphy.get("refinement"),
                    "iou_pred": iou(p >= 0.5, truth, theta),
                    "false_inclusion_pred": fi,
                    "gate_status": "ok", "exclusion_reason": None,
                    "unavailable_reason": None,
                })

    del model, draws_sel, draws_val
    gc.collect()
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True, help="C1..C4, S1..S3")
    ap.add_argument("--limit", type=int, default=100, help="campaigns per arm")
    ap.add_argument("--arms", default=None, help="comma-separated subset")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--smoke", action="store_true",
                    help="tiny settings. NEVER a publishable artefact (spec §19 step 11)")
    args = ap.parse_args()

    conds = conditions()
    if args.condition not in conds:
        raise SystemExit(f"unknown condition {args.condition}; have {sorted(conds)}")
    cond = conds[args.condition]
    arms = tuple(args.arms.split(",")) if args.arms else tuple(ARMS)

    out = args.out or (OUT_DEFAULT.with_name(
        f"final-spade-{args.condition.lower()}{'-SMOKE' if args.smoke else ''}.json"))
    ckpt = out.with_suffix(".ckpt.jsonl")

    global GRID_N, SUBSET_N, N_DRAWS_HALF
    if args.smoke:
        GRID_N, SUBSET_N, N_DRAWS_HALF = 2048, 256, 128

    dim = cond["dim"]
    grid = sobol_grid(dim, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(dim, SUBSET_N, seed=GRID_SEED)
    head, dirty = _head(), _dirty()

    keys = _keys(cond["family"], args.limit)
    done = set()
    if ckpt.exists():
        for line in ckpt.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["instance_seed"], r["campaign_seed"], r["arm"]))

    print(f"{STUDY_ID} · {args.condition} · {cond['family']} d={dim} "
          f"sigma={cond['sigma']} · tier={cond['tier']}")
    print(f"{len(arms)} arms x {len(keys)} campaigns · draws={2*N_DRAWS_HALF} "
          f"(split {N_DRAWS_HALF}/{N_DRAWS_HALF}) · grid={GRID_N}")
    print(f"regime by tau_frac: "
          f"{ {k: v['regime_class'] for k, v in cond['by_tau'].items()} }")
    if args.smoke:
        print("🔴 SMOKE -- not a publishable artefact")
    if dirty:
        print("⚠️  working tree dirty; code_commit is not a faithful fingerprint")
    print()

    total, t0, n_done = len(arms) * len(keys), time.time(), 0
    with ckpt.open("a") as fh:
        for instance, seed in keys:
            # Truth is built once per (instance, seed) and shared across arms -- it is a
            # property of the landscape, not of the campaign.
            orc_t = _oracle(cond["family"], instance, dim, cond["sigma"], seed)
            with torch.no_grad():
                truth = orc_t.truth(grid).reshape(-1).double()
                truth_sub = orc_t.truth(X_sub).reshape(-1).double()
            for arm in arms:
                n_done += 1
                if (instance, seed, arm) in done:
                    continue
                rows = score(cond, instance, arm, seed, grid, X_sub, truth, truth_sub,
                             cond["by_tau"], head)
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
                fh.flush()
                el = time.time() - t0
                print(f"[{n_done:4d}/{total}] {arm:<20} {str(instance)[:12]:<12} "
                      f"seed={seed:<3} rows={len(rows)} "
                      f"({el/60:.1f}m, eta {(el/max(n_done,1))*(total-n_done)/60:.0f}m)")

    rows = [json.loads(l) for l in ckpt.read_text().splitlines() if l.strip()]
    missing = sorted(set(ARMS) - {r["arm"] for r in rows})
    out.write_text(json.dumps({
        "study_id": STUDY_ID, "registration_commit": REGISTRATION_COMMIT,
        "code_commit": head, "dirty": dirty, "smoke": bool(args.smoke),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "condition": args.condition, "condition_spec": cond,
        "config": {"arms": list(arms), "n_campaigns": len(keys),
                   "tau_qs": list(TAU_QS), "gammas": list(GAMMAS),
                   "alphas": list(ALPHAS), "n_draws": 2 * N_DRAWS_HALF,
                   "selection_draws": N_DRAWS_HALF, "evaluation_draws": N_DRAWS_HALF,
                   "grid_n": GRID_N, "subset_n": SUBSET_N, "grid_seed": GRID_SEED,
                   "n_plate1": N_PLATE1, "n_plate2": N_PLATE2, "budget": BUDGET,
                   "design_tau_frac": DESIGN_TAU_FRAC, "cand_n": CAND_N},
        "schema": list(ROW_SCHEMA),
        "missing_mandatory_arms": missing,
        "gate_failures": [],
        "rows": rows,
    }, indent=1))
    print(f"\nwrote {out.name} · {len(rows)} rows")
    if missing:
        print(f"⚠️  MISSING MANDATORY ARMS: {missing} -- blocks a primary conclusion (§13.6)")


if __name__ == "__main__":
    main()
