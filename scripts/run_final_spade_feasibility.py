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

TAU_FRACS = (0.60, 0.75)
GAMMAS_PRIMARY = (0.50, 0.95)
GAMMA_DIAGNOSTIC = 0.99

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
    straddle, nonempty = [], {tf: [] for tf in TAU_FRACS}

    for instance, seed in _keys(family, PILOT_N):
        orc = _oracle(family, instance, dim, sigma, seed)
        mu_max = _mu_max(family, instance, dim)
        X1 = static_design(bounds, "lhs", N_PLATE1, seed)
        Y1, V1 = orc.evaluate(X1)
        model = build_gp(X1, Y1, V1, bounds)
        ad = gp_adapter(model)

        mean_g, sd_g = ad.posterior_mean_and_sd(grid)
        # The straddle band at the DESIGN threshold -- what plate 2 exists to resolve.
        theta_design = 0.75 * mu_max
        straddle.append(float(((mean_g - theta_design).abs()
                               <= STRADDLE_Z * sd_g).double().mean()))

        with torch.no_grad():
            post = model.posterior(X_sub)
            cov = post.mvn.covariance_matrix.double()
            cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
            L = torch.linalg.cholesky(cov)
            g = torch.Generator().manual_seed(seed)
            z = torch.randn(cov.shape[0], PILOT_DRAWS, generator=g, dtype=torch.double)
            draws = (post.mean.reshape(-1, 1).double() + L @ z).T

        for tf in TAU_FRACS:
            ce = conservative_estimate(draws, tf * mu_max, PILOT_ALPHA)
            nonempty[tf].append(bool(int(ce.sum()) > 0))

        del model, draws

    return {"n_pilot": len(straddle),
            "boundary_frac_mean": float(sum(straddle) / len(straddle)),
            "boundary_frac_per_campaign": straddle,
            "nonempty_rate": {str(tf): sum(v) / len(v) for tf, v in nonempty.items()},
            "nonempty_count": {str(tf): int(sum(v)) for tf, v in nonempty.items()},
            "pilot_draws": PILOT_DRAWS, "pilot_alpha": PILOT_ALPHA}


def main() -> None:
    t0 = time.time()
    head, rows = _head(), []
    print(f"{STUDY_ID} · feasibility gate · registration {REGISTRATION_COMMIT}")
    print(f"{len(CONDITIONS)} conditions x {len(TAU_FRACS)} tau_frac · pilot n={PILOT_N} "
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

        for tf in TAU_FRACS:
            facts = threshold_facts(tf, mu_max, sigma,
                                    GAMMAS_PRIMARY + (GAMMA_DIAGNOSTIC,), truth)
            # The classifier sees ONLY the primary gammas: gamma=0.99 is a registered
            # diagnostic (spec §2), and letting a diagnostic corner decide feasibility
            # would exclude cells the study never claimed there.
            primary_ceilings = {g: facts["tau_max_by_gamma"][g] for g in GAMMAS_PRIMARY}
            cls, reason = classify_regime(
                tau=facts["tau_raw"], tau_max_by_gamma=primary_ceilings,
                prevalence=facts["true_prevalence"],
                nonempty_rate=p["nonempty_rate"][str(tf)],
                boundary_frac=p["boundary_frac_mean"],
                structural_exception=cond["exception"])

            row = {"study_id": STUDY_ID, "registration_commit": REGISTRATION_COMMIT,
                   "code_commit": head, "condition_id": cond["id"], "tier": cond["tier"],
                   "why_included": cond["why"], "family": family, "dimension": dim,
                   "sigma": sigma, "mu_max": mu_max,
                   "tau_definition": "tau = tau_frac * mu_max (FRACTION, never absolute)",
                   **facts,
                   "tau_max_primary": primary_ceilings,
                   "gammas_primary": list(GAMMAS_PRIMARY),
                   "gamma_diagnostic": GAMMA_DIAGNOSTIC,
                   "expected_nonempty_rate": p["nonempty_rate"][str(tf)],
                   "nonempty_count": p["nonempty_count"][str(tf)],
                   "boundary_frac": p["boundary_frac_mean"],
                   "pilot": {k: v for k, v in p.items()
                             if k != "boundary_frac_per_campaign"},
                   "regime_class": cls, "classification_reason": reason,
                   "structural_exception": cond["exception"]}
            rows.append(row)
            flag = {"TARGET": "**", "EXCEPTION": " !", "INFEASIBLE": " X"}.get(cls, "  ")
            print(f"{flag} {cond['id']:<3} {family:<11} d={dim} s={sigma:<5} "
                  f"tf={tf:<5} tau={facts['tau_raw']:.4f} "
                  f"ceil={facts['tau_max_worst']:.4f} prev={facts['true_prevalence']:.4f} "
                  f"ne={p['nonempty_rate'][str(tf)]:.2f} "
                  f"bnd={p['boundary_frac_mean']:.4f}  {cls}")

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
                   "tau_fracs": list(TAU_FRACS),
                   "gammas_primary": list(GAMMAS_PRIMARY),
                   "gamma_diagnostic": GAMMA_DIAGNOSTIC,
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
