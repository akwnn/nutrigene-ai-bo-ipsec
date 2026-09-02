"""The pre-run feasibility gate for `spade-final-2026-08-23`.

    .venv/bin/python scripts/run_final_spade_feasibility.py

Writes ``results/final-spade-feasibility.json``.

------------------------------------------------------------------------------
WHY THIS RUNS BEFORE THE CAMPAIGNS, AND NOT AFTER
------------------------------------------------------------------------------

Two failures this project has already committed are prevented here, and only here.

**A threshold above the ceiling is a property of the threshold.** FINDINGS §4.5: an earlier
registration used absolute thresholds {0.70, 0.80, 0.85, 0.90} and **all four sat above
`tau_max`**. Every arm would have certified nothing and the published table would have been
zeros -- read, inevitably, as a method failure. §9.8 then found **111 of 384 cells (28.9%)
above the ceiling** once `tau_q` equalised prevalence instead of level. A cell that cannot be
certified by *anything* must be excluded **before** an arm is scored in it, or the zero
becomes evidence.

**A regime class assigned after the fact means "where SPADE won".** So every input to
:func:`boec.final_spade.classify_regime` is computed here, from oracle geometry and a
plate-1-only pilot, and the classifier takes no arm outcome at all.

------------------------------------------------------------------------------
WHAT THE PILOT IS, AND ITS ONE DECLARED DEVIATION
------------------------------------------------------------------------------

20 campaigns of ``spade_plate1_only`` at seeds 0-19, frozen. From each: the straddle-band
fraction (what plate 2 exists to resolve) and whether a conservative estimate is non-empty.

**The pilot uses 1,024 draws, not the study's 4,096, and that is a deliberate declared
choice.** These are *planning* statistics read against coarse bars (0.05 and 0.50), not
results; §29 established 1,024 as the point where containment estimates stop being
artefacts, which is ample for a yes/no bar but is **not** enough for a certificate claim and
is never reported as one. No number from this file may appear in a containment table.

**Emptiness is measured at `alpha = 0.95`, the stringent assurance.** A larger `alpha`
demands a smaller set, so it is the binding corner: a cell whose certificates survive 0.95
survives 0.80 too. Classifying on the easier corner would admit cells that go empty exactly
where the study's high-assurance claim lives.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import gp_adapter                              # noqa: E402
from boec.final_spade import classify_regime, threshold_facts        # noqa: E402
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import family_evaluator, instance_by_id, unit_bounds  # noqa: E402
from boec.runner import static_design                                # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402
from boec.vorobev import conservative_estimate                       # noqa: E402

OUT = ROOT / "results" / "final-spade-feasibility.json"
P2_COMMITTED = ROOT / "results" / "p2-versionb-gamma.json"

STUDY_ID = "spade-final-2026-08-23"
REGISTRATION_COMMIT = "c4f58d3"

#: Spec §5.2 / §5.3. `exception` is a PRE-DECLARED structural reason, written here before
#: any pilot number exists. Declaring one after seeing results is a protocol violation.
CONDITIONS = (
    {"id": "C1", "family": "hill", "dim": 6, "sigma": 0.25, "tier": "primary",
     "exception": None,
     "why": "continuity -- the one point where SPADE's certificate has ever been measured"},
    {"id": "C2", "family": "hill", "dim": 6, "sigma": 0.10, "tier": "primary",
     "exception": None,
     "why": "main TARGET candidate -- §13 has SPADE 1st-3rd of 12 on the map here"},
    {"id": "C3", "family": "hartmann6", "dim": 6, "sigma": 0.25, "tier": "primary",
     "exception": None,
     "why": "cross-family stress -- §37/§42 predict SPADE struggles"},
    {"id": "C4", "family": "hartmann6", "dim": 8, "sigma": 0.25, "tier": "primary",
     "exception": None,
     "why": "dimension stress -- doe_unscreened expected unavailable"},
    {"id": "S1", "family": "ackley", "dim": 6, "sigma": 0.25, "tier": "secondary",
     "exception": ("centre-point optimum advantages classical designs; §41 records SPADE "
                   "certifying NOTHING in 1,200 campaigns on this family"),
     "why": "the known exception, reported rather than hidden"},
    {"id": "S2", "family": "levy", "dim": 6, "sigma": 0.25, "tier": "secondary",
     "exception": None, "why": "candidate for the §5.3 levy-or-rosenbrock slot"},
    {"id": "S3", "family": "rosenbrock", "dim": 6, "sigma": 0.25, "tier": "secondary",
     "exception": None, "why": "candidate for the §5.3 levy-or-rosenbrock slot"},
)

#: 🔴 ERRATUM 1. Was `TAU_FRACS = (0.60, 0.75)` as fractions of mu_max. At sigma=0.25 the
#: gamma=0.95 ceiling is 0.5888 and BOTH sat above it, so 12 of 14 cells returned
#: INFEASIBLE -- §4.5's defect, recurring. The estimand is now `tau_q`, P5's per-family
#: prevalence quantile, read from the COMMITTED table and never recomputed here.
TAU_QS = (0.10, 0.25)
TAU_TABLE = ROOT / "results" / "p5-tau-quantile.json"

#: 🔴 ERRATUM 1. Primary gamma is sigma-dependent, because at sigma=0.25 the 0.95 ceiling
#: (0.5888) sits at a true prevalence of ~0.71 on hill: EVERY threshold certifiable there
#: describes a region covering >70% of the box, so insisting on gamma=0.95 would test the
#: ceiling rather than the method. gamma=0.95 is retained as a reported diagnostic.
GAMMAS_BY_SIGMA = {0.25: (0.50,), 0.10: (0.50, 0.95)}
GAMMAS_DIAGNOSTIC = (0.95, 0.99)

N_PLATE1 = 40
PILOT_N = 20
PILOT_DRAWS = 1024          # declared deviation -- see the module docstring
PILOT_ALPHA = 0.95          # the binding corner
GRID_N, SUBSET_N, GRID_SEED = 20_000, 2_000, 0
STRADDLE_Z = 1.96


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def _keys(family: str, n: int) -> list[tuple]:
    """`hill` is an ENSEMBLE keyed by hashed instance ids; every other family is one
    landscape keyed by seed. P8 records what happens when this is got wrong: asking
    `instance_by_id` for an instance called "hill"."""
    if family == "hill":
        ks = sorted({(r["instance"], r["seed"]) for r in
                     json.loads(P2_COMMITTED.read_text())["rows"]})
        return ks[:n]
    return [(family, s) for s in range(n)]


def _oracle(family: str, instance: str, dim: int, sigma: float, seed: int):
    if family == "hill":
        return BiphasicOracle(instance_by_id(instance, dim), sigma_rel=sigma, seed=seed)
    return family_evaluator(family, dim, sigma, seed)


def committed_tau_q(family: str, dim: int, p: float, instance: str | None) -> float:
    """The COMMITTED `tau_q`. Raises rather than recomputing a cell the table lacks.

    Recomputing would let this study's threshold drift from the one P5 registered and P6
    was scored at, and the drift would be invisible. §9.8's gate on that table was
    `worst |achieved prevalence - p| = 0.000e+00` -- exact -- and it stays that way only if
    the number is read, never re-derived.
    """
    d = json.loads(TAU_TABLE.read_text())
    for r in d["rows"]:
        if (r["family"] == family and r["dim"] == dim and r["p"] == p
                and (instance is None or r.get("instance") in (None, instance))):
            return float(r["tau_q"])
    raise SystemExit(
        f"no committed tau_q for family={family!r} d={dim} p={p} in {TAU_TABLE.name}; "
        "this study reads that table and does not recompute it (Erratum 1)")


def _mu_max(family: str, instance: str, dim: int) -> float:
    """`UnitScaled` puts every non-hill family's optimum at exactly 1.0."""
    if family == "hill":
        return float(instance_by_id(instance, dim).optimum_value)
    return 1.0


def pilot(cond: dict, grid: torch.Tensor, X_sub: torch.Tensor) -> dict:
    """20 plate-1-only campaigns. Returns straddle fraction and non-empty rate per
    tau_frac, plus the per-campaign values so the summary is auditable."""
    family, dim, sigma = cond["family"], cond["dim"], cond["sigma"]
    bounds = unit_bounds(dim)
    # 🔴 DEFECT FOUND AND FIXED, first feasibility re-run. The straddle band was measured
    # once per campaign at `0.75 * mu_max` -- a leftover from the tau_frac parameterisation
    # Erratum 1 replaced. Under `tau_q` the actual threshold on hartmann6 at p=0.25 is
    # 0.0971, so a band measured at 0.75 sat far outside the data and returned
    # `boundary_frac = 0.0000` on hartmann6 and ackley. That is not "no boundary
    # uncertainty"; it is the band measured at the wrong threshold, and it would have
    # pushed both families out of TARGET for a reason that was an artefact of my own code.
    # The band is now computed PER tau_q, at the threshold actually being classified.
    straddle, nonempty = {p_: [] for p_ in TAU_QS}, {p_: [] for p_ in TAU_QS}

    for instance, seed in _keys(family, PILOT_N):
        orc = _oracle(family, instance, dim, sigma, seed)
        mu_max = _mu_max(family, instance, dim)
        X1 = static_design(bounds, "lhs", N_PLATE1, seed)
        Y1, V1 = orc.evaluate(X1)
        model = build_gp(X1, Y1, V1, bounds)
        ad = gp_adapter(model)

        mean_g, sd_g = ad.posterior_mean_and_sd(grid)

        with torch.no_grad():
            post = model.posterior(X_sub)
            cov = post.mvn.covariance_matrix.double()
            cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
            L = torch.linalg.cholesky(cov)
            g = torch.Generator().manual_seed(seed)
            z = torch.randn(cov.shape[0], PILOT_DRAWS, generator=g, dtype=torch.double)
            draws = (post.mean.reshape(-1, 1).double() + L @ z).T

        for p_ in TAU_QS:
            tau = committed_tau_q(family, dim, p_,
                                  instance if family == "hill" else None)
            # The straddle band AT THIS THRESHOLD -- what plate 2 exists to resolve.
            straddle[p_].append(
                float(((mean_g - tau).abs() <= STRADDLE_Z * sd_g).double().mean()))
            ce = conservative_estimate(draws, tau, PILOT_ALPHA)
            nonempty[p_].append(bool(int(ce.sum()) > 0))

        del model, draws

    return {"n_pilot": len(next(iter(nonempty.values()))),
            "boundary_frac_mean": {str(k): float(sum(v) / len(v))
                                   for k, v in straddle.items()},
            "boundary_frac_per_campaign": {str(k): v for k, v in straddle.items()},
            "nonempty_rate": {str(k): sum(v) / len(v) for k, v in nonempty.items()},
            "nonempty_count": {str(k): int(sum(v)) for k, v in nonempty.items()},
            "pilot_draws": PILOT_DRAWS, "pilot_alpha": PILOT_ALPHA}


def main() -> None:
    t0 = time.time()
    head, rows = _head(), []
    print(f"{STUDY_ID} · feasibility gate · registration {REGISTRATION_COMMIT}")
    print(f"{len(CONDITIONS)} conditions x {len(TAU_QS)} tau_q · pilot n={PILOT_N} "
          f"at {PILOT_DRAWS} draws, alpha={PILOT_ALPHA}\n")

    for cond in CONDITIONS:
        family, dim, sigma = cond["family"], cond["dim"], cond["sigma"]
        grid = sobol_grid(dim, GRID_N, seed=GRID_SEED)
        X_sub = sobol_grid(dim, SUBSET_N, seed=GRID_SEED)
        instance = _keys(family, 1)[0][0]
        orc = _oracle(family, instance, dim, sigma, 0)
        mu_max = _mu_max(family, instance, dim)
        with torch.no_grad():
            truth = orc.truth(grid).reshape(-1).double()

        p = pilot(cond, grid, X_sub)

        gammas_primary = GAMMAS_BY_SIGMA[sigma]
        all_gammas = tuple(sorted(set(gammas_primary) | set(GAMMAS_DIAGNOSTIC)))

        for p_q in TAU_QS:
            tau = committed_tau_q(family, dim, p_q,
                                  instance if family == "hill" else None)
            # threshold_facts is driven by a FRACTION; tau_q is an absolute level, so it
            # is expressed as tau/mu_max here. That returns tau_raw == tau exactly and
            # leaves the tested function untouched.
            facts = threshold_facts(tau / mu_max, mu_max, sigma, all_gammas, truth)
            facts["tau_q_p"] = p_q
            facts["tau_definition_detail"] = (
                f"tau_q at p={p_q}, read from {TAU_TABLE.name} (Erratum 1); "
                "NOT recomputed here")
            primary_ceilings = {g: facts["tau_max_by_gamma"][g] for g in gammas_primary}
            cls, reason = classify_regime(
                tau=facts["tau_raw"], tau_max_by_gamma=primary_ceilings,
                prevalence=facts["true_prevalence"],
                nonempty_rate=p["nonempty_rate"][str(p_q)],
                boundary_frac=p["boundary_frac_mean"][str(p_q)],
                structural_exception=cond["exception"])

            row = {"study_id": STUDY_ID, "registration_commit": REGISTRATION_COMMIT,
                   "code_commit": head, "condition_id": cond["id"], "tier": cond["tier"],
                   "why_included": cond["why"], "family": family, "dimension": dim,
                   "sigma": sigma, "mu_max": mu_max,
                   "tau_definition": "tau_q -- per-family prevalence quantile (Erratum 1)",
                   **facts,
                   "tau_max_primary": primary_ceilings,
                   "gammas_primary": list(gammas_primary),
                   "gammas_diagnostic": list(GAMMAS_DIAGNOSTIC),
                   "expected_nonempty_rate": p["nonempty_rate"][str(p_q)],
                   "nonempty_count": p["nonempty_count"][str(p_q)],
                   "boundary_frac": p["boundary_frac_mean"][str(p_q)],
                   "pilot": {k: v for k, v in p.items()
                             if k != "boundary_frac_per_campaign"},
                   "regime_class": cls, "classification_reason": reason,
                   "structural_exception": cond["exception"]}
            rows.append(row)
            flag = {"TARGET": "**", "EXCEPTION": " !", "INFEASIBLE": " X"}.get(cls, "  ")
            print(f"{flag} {cond['id']:<3} {family:<11} d={dim} s={sigma:<5} "
                  f"p={p_q:<5} tau={facts['tau_raw']:.4f} "
                  f"ceil={min(primary_ceilings.values()):.4f} "
                  f"prev={facts['true_prevalence']:.4f} "
                  f"ne={p['nonempty_rate'][str(p_q)]:.2f} "
                  f"bnd={p['boundary_frac_mean'][str(p_q)]:.4f}  {cls}")

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["regime_class"]] = counts.get(r["regime_class"], 0) + 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "study_id": STUDY_ID, "registration_commit": REGISTRATION_COMMIT,
        "code_commit": head, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "elapsed_s": round(time.time() - t0, 1),
        "environment": {"python": platform.python_version(),
                        "torch": torch.__version__, "platform": platform.platform()},
        "config": {"conditions": [c["id"] for c in CONDITIONS],
                   "tau_qs": list(TAU_QS),
                   "gammas_by_sigma": {str(k): list(v) for k, v in GAMMAS_BY_SIGMA.items()},
                   "gammas_diagnostic": list(GAMMAS_DIAGNOSTIC),
                   "pilot_n": PILOT_N, "pilot_draws": PILOT_DRAWS,
                   "pilot_alpha": PILOT_ALPHA, "n_plate1": N_PLATE1,
                   "grid_n": GRID_N, "subset_n": SUBSET_N, "grid_seed": GRID_SEED,
                   "straddle_z": STRADDLE_Z},
        "pilot_draws_note": (
            "1024 draws, NOT the study's 4096. These are PLANNING statistics read against "
            "coarse bars and must never appear in a containment table -- see the module "
            "docstring."),
        "counts": counts, "rows": rows,
    }, indent=1))
    print(f"\n{counts}")
    print(f"wrote {OUT.name} · {len(rows)} rows · {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
