"""Version B — the two-plate arm. The test that can actually settle SPADE.

Registered in `docs/OPEN-QUESTIONS.md` before `src/boec/lse.py` existed.

K6 and K6b tested plate 1 only. SPADE v2 is two plates, so plate 1 losing to qLogNEI in
15 of 24 cells does not settle it. Plate 2 is the machinery meant to repair a weak
certified region and it had never been run.

BUDGET: 40 + 8 = 48. The second plate comes OUT of the design, never on top. Any
comparison that adds wells is not budget-matched and must not be a headline.

ROUNDS ARE REPORTED. Every K6 contrast was at equal wells only. plate1_only is 1 round,
versionb is 2, doe is 3, qlognei is 10.

------------------------------------------------------------------------------
AMENDMENT E, PHASE 1.1 + 1.5 — registered at `d624fa2`, before this file changed
------------------------------------------------------------------------------

**E6 adds a SIXTH arm, `versionb_predictive`, and replaces nothing.** The published
straddle uses the GP's `sd` alone -- the estimation term -- so `versionb` resolves the
**latent** contour while the registered deliverable is Peterson's **predictive**
`D_gamma`. The new arm targets the deliverable's own boundary with
`1.96*sqrt(sd^2 + sigma(x)^2) - |mu - theta|`, `sigma` an array because this repo's noise
is relative. It runs LAST in the arm loop so it cannot perturb any arm above it, and
`versionb` is untouched so the committed column stays comparable.

**E1 adds per-campaign flatness logging.** At n=40 the neighbour density is 0.378 per
fitted lengthscale, at which `s(x)` may sit at the prior everywhere and the eight wells
would be chosen by numerical noise -- a space-filling draw wearing a criterion's name.
`acq_cv = SD(a)/|mean(a)|` on the candidate grid decides, against the registered threshold
`ACQ_CV_FLAT`, and a campaign below it reports "acquisition uninformative at this density"
instead of contributing a silent null.

**E2 adds the batch-geometry logging its own Fix asked for**: the achieved minimum
pairwise Chebyshev distance of every plate-2 batch, the radius that produced it, whether
the top-q batch would have violated that radius, and the plate-2 coordinates themselves.
The E2 claim that the exclusion is inert does not reproduce -- it binds in 22 of 50
campaigns -- and this file is where that stops being an argument.

**THIS RUNNER NEVER WRITES `results/versionb.json`.** That file carries the headline
containment result and is the comparator, not the target. It is loaded read-only as a
**gate**: every column the five shared arms have in common with it must agree at
`|delta| = 0.0`, and a single failure stops the run. Section 6.16 of the technical report
recorded that Version B was the one production run in this project without a gate. It has
one now.
"""

from __future__ import annotations

import argparse, gc, json, math, platform, subprocess, sys, time
from pathlib import Path

import numpy as np
import torch

from boec.designspace import gp_adapter, brier_and_auc, predictive_probability_map
from boec.certstraddle import batch_lse_rho, certificate_straddle
from boec.lse import (batch_lse, exclusion_radius, min_pairwise_chebyshev,
                      predictive_sigma, straddle_predictive_score, straddle_score)
from boec.norms import sobol_grid
from boec.replay import committed_rows, instance_by_id, regenerate, scored_curve, unit_bounds
from boec.runner import static_design
from boec.surrogate import build_gp
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar
from boec.vorobev import (alpha_star, conservative_estimate, containment_probability,
                          empirical_containment, excursion_probability, vorobev_deviation)

#: NEVER the output. Loaded read-only as the gate. See the module docstring.
COMMITTED = Path("results/versionb.json")
OUT_DEFAULT = Path("results/versionb-predictive.json")
N_PLATE1, N_PLATE2, BUDGET = 40, 8, 48
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
#: Threshold the LSE criterion TARGETS. Registered; scoring still spans all TAU_FRACS.
DESIGN_TAU_FRAC = 0.75
#: DELIBERATELY ABSENT. An earlier revision defined GAMMA_FOR_AUC = 0.90 and never used
#: it, so the AUC actually computed was at the gamma=0.50 row -- the lowest-assurance
#: corner, and the one where plain LHS already beat qLogNEI. The constant is removed
#: rather than wired in, because by Amendment C2's algebra the latent threshold is
#: theta = tau_frac * mu_max for EVERY gamma, so AUC against the true excursion set does
#: not depend on gamma at all. A gamma constant here would imply a dependence that does
#: not exist. What DOES depend on gamma is the absolute tau a lab may promise, and that
#: is reported in the write-up, not computed here.
GRID_N, SUBSET_N, N_DRAWS, GRID_SEED = 20_000, 2_000, 512, 0
CAND_N = 4096
ALPHAS = (0.50, 0.80, 0.95)
#: Amendment E1, registered at `d624fa2` from the Matern 5/2 kernel and NOT from the data.
#: One fitted lengthscale of contrast in s spans 0.9903 - 0.8517 = 0.1386 s_prior, so the
#: straddle's 1.96*s term spans 0.2717 s_prior against a mean of at most 1.96 s_prior;
#: spreading that range over the grid gives SD = range/sqrt(12) and acq_cv = 0.0400.
#: Below it, no candidate is even one lengthscale better determined than the typical one.
ACQ_CV_FLAT = 0.04
#: `versionb_predictive` is LAST so it cannot perturb the five arms above it.
ARMS = ("versionb", "versionb_random", "plate1_only", "doe", "qlognei",
        "versionb_predictive")
ROUNDS = {"versionb": 2, "versionb_random": 2, "versionb_predictive": 2,
          "plate1_only": 1, "doe": 3, "qlognei": 10}
#: Diagnostics, provenance and the new arm are not comparable to the committed file.
UNGATED_KEYS = {"instance", "seed", "arm", "plate2_X", "plate2_mode"}


def _head():
    return subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()


def _fit(X, Y, Yvar, d):
    return build_gp(X, Y, Yvar, unit_bounds(d))


def _plate2_diag(X2, radius=None, topq=None, score=None):
    """The E1/E2 diagnostics for one plate-2 batch. Every claim recomputable from these."""
    d = {"plate2_min_cheb": min_pairwise_chebyshev(X2),
         "plate2_X": X2.tolist(),
         "excl_radius": radius,
         "topq_min_cheb": None if topq is None else min_pairwise_chebyshev(topq),
         "acq_cv": None, "acq_sd": None, "acq_mean": None, "acq_flat": None}
    if radius is not None and topq is not None:
        # E2: did the exclusion have anything to do? True means the score alone would
        # have stacked wells closer together than the model's own lengthscale allows.
        d["excl_bound"] = bool(d["topq_min_cheb"] < radius)
    else:
        d["excl_bound"] = None
    if score is not None:
        sd, mu = float(score.std()), float(score.mean())
        d["acq_sd"], d["acq_mean"] = sd, mu
        # E1: relative dispersion. |mean| ~ 0 is a knife-edge, not the flat limit; it
        # inflates the ratio and so can only UNDER-report flatness, never over-report it.
        d["acq_cv"] = float("inf") if mu == 0.0 else sd / abs(mu)
        d["acq_flat"] = bool(d["acq_cv"] < ACQ_CV_FLAT)
    return d


#: Every plate-2 rule this function knows. The dispatch below used to be
#: `if mode == "random": ... else: <latent straddle>`, so ANY unrecognised string -- a typo,
#: a stale config value, a renamed arm -- silently produced a row labelled with that string
#: and computed by the committed `versionb` criterion. That is the same class of defect as
#: this project's three existing errata (`EV(x)` reading ground truth, `exclusion_radius`
#: hardcoded to 0.1, `above_ceiling` copied across rows), and it is why KV §4 makes an
#: arm-distinctness assertion mandatory. Unknown modes now raise.
PLATE2_MODES = ("lse", "predictive", "random", "cert")

#: KV §3: the Vorob'ev level `mode="cert"` straddles. REGISTERED at 0.95 -- the assurance
#: level the certificate is scored at -- not swept, and not selected after seeing an outcome.
#: At 0.5 `batch_lse_rho` is bit-identical to the committed `batch_lse`, so this constant is
#: the only thing separating the new arm from the old one.
CERT_RHO = 0.95


def _two_plate(orc, dim, seed, mu_max, mode: str):
    """Plate 1 space-filling; plate 2 by the latent straddle, the predictive straddle, or
    at random. Returns ``(X, Y, Yvar, diag)``.

    ``mode="lse"`` is bit-for-bit what produced the committed ``versionb`` column: same
    design, same candidate grid, same criterion, same radius. The diagnostics are read
    off the same deterministic (mean, sd) the batch was chosen from, so they describe the
    batch that was actually taken rather than a re-derivation of it.
    """
    if mode not in PLATE2_MODES:
        raise ValueError(
            f"unknown plate-2 mode {mode!r}; expected one of {PLATE2_MODES}. Falling through "
            "to the latent straddle would label a row with this mode and compute it with "
            "another arm's criterion.")

    bounds = unit_bounds(dim)
    X1 = static_design(bounds, "lhs", N_PLATE1, seed)
    Y1, V1 = orc.evaluate(X1)
    model = _fit(X1, Y1, V1, dim)

    if mode == "random":
        g = torch.Generator().manual_seed(10_000 + seed)
        X2 = torch.rand(N_PLATE2, dim, generator=g, dtype=torch.double)
        diag = _plate2_diag(X2)
    else:
        cand = sobol_grid(dim, CAND_N, seed=seed)
        theta = DESIGN_TAU_FRAC * mu_max
        radius = exclusion_radius(model)
        ad = gp_adapter(model)
        mean, sd = ad.posterior_mean_and_sd(cand)
        if mode == "predictive":
            sig = predictive_sigma(mean, orc.sigma_rel, orc.sigma_add)
            score = straddle_predictive_score(mean, sd, theta, sig)
            X2 = batch_lse(ad, cand, theta, N_PLATE2, exclude=radius, sigma=sig)
        elif mode == "cert":
            # KV §3. The certificate's frontier is `{p(x) >= rho_alpha}`, not the p=0.5
            # contour Bryan's straddle targets. rho is REGISTERED at 0.95, not swept.
            sig = None
            score = certificate_straddle(mean, sd, theta, CERT_RHO)
            X2 = batch_lse_rho(ad, cand, theta, N_PLATE2, exclude=radius, rho=CERT_RHO)
        else:
            sig = None
            score = straddle_score(mean, sd, theta)
            X2 = batch_lse(ad, cand, theta, N_PLATE2, exclude=radius, sigma=sig)
        topq = cand[torch.topk(score, N_PLATE2).indices]
        diag = _plate2_diag(X2, radius=radius, topq=topq, score=score)
        del cand, mean, sd, score, topq
    diag["plate2_mode"] = mode

    Y2, V2 = orc.evaluate(X2)
    del model; gc.collect()
    return torch.cat([X1, X2]), torch.cat([Y1, Y2]), torch.cat([V1, V2]), diag


def _score(X, Y, Yvar, orc, dim, mu_max, grid, truth, X_sub, truth_sub, seed,
           kept=None, held=None):
    """Score one campaign. `kept`/`held` apply Amendment B3: an arm that never varied a
    factor is evaluated on its ACTIVE SUBSPACE, with screened-out coordinates pinned."""
    model = _fit(X, Y, Yvar, dim)
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, Z): return mean, sd

    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    X_eval = X_sub
    t_eval = truth_sub
    if kept is not None and held:
        X_eval = X_sub.clone()
        for j, v in held.items():
            X_eval[:, j] = v
        with torch.no_grad():
            t_eval = orc.truth(X_eval).reshape(-1).double()

    with torch.no_grad():
        post = model.posterior(X_eval)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        g = torch.Generator().manual_seed(seed)
        z = torch.randn(cov.shape[0], N_DRAWS, generator=g, dtype=torch.double)
        draws = (post.mean.reshape(-1, 1).double() + L @ z).T

    out = {"regret": float(mu_max - scored_curve(orc, X, Y)[-1]), "n_wells": int(X.shape[0]),
           "n_active": dim if kept is None else len(kept)}
    for tf in TAU_FRACS:
        theta = tf * mu_max
        p = predictive_probability_map(_M(), grid, theta, sigma_pred)
        b, a = brier_and_auc(p, truth, theta)
        out[f"auc_{tf}"] = a
        out[f"brier_{tf}"] = b
        out[f"alpha_star_{tf}"] = alpha_star(draws, theta)
        out[f"vorobev_dev_{tf}"] = vorobev_deviation(draws, theta)
        for a in ALPHAS:
            ce = conservative_estimate(draws, theta, a)
            n_ce = int(ce.sum())
            out[f"ce_vol_{tf}_{a}"] = n_ce / ce.numel()
            out[f"ce_empty_{tf}_{a}"] = n_ce == 0
            # CIRCULAR -- conservative_estimate selects on this. Kept, labelled, so the
            # tautology is visible rather than silently removed.
            out[f"ce_contain_{tf}_{a}"] = (containment_probability(draws, ce, theta)
                                           if n_ce else float("nan"))
            # THE REAL TEST: is the set actually inside the TRUE excursion set?
            emp = empirical_containment(ce, t_eval, theta)
            out[f"ce_empirical_{tf}_{a}"] = float("nan") if emp is None else float(emp)
    del model, draws, mean, sd; gc.collect()
    return out


def _load_gate(path: Path) -> dict:
    """`(instance, seed, arm) -> committed row`. Missing file is a hard error, not a skip.

    A gate that silently degrades to "no comparison available" is not a gate; the whole
    point is that the five shared arms cannot drift without the run stopping.
    """
    if not path.exists():
        raise SystemExit(f"gate file {path} is missing; refusing to run ungated")
    return {(r["instance"], r["seed"], r["arm"]): r
            for r in json.loads(path.read_text())["rows"]}


def _gate(row: dict, ref: dict | None) -> list[str]:
    """Every shared numeric column at `|delta| = 0.0`. No tolerance is introduced."""
    if ref is None:
        return []
    bad = []
    for k, v in row.items():
        if k in UNGATED_KEYS or k not in ref or v is None or ref[k] is None:
            continue
        a, b = v, ref[k]
        if isinstance(a, bool) or isinstance(b, bool):
            if bool(a) != bool(b):
                bad.append(f"{k}: {a!r} != committed {b!r}")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if math.isnan(float(a)) and math.isnan(float(b)):
                continue
            if float(a) != float(b):
                bad.append(f"{k}: {a!r} != committed {b!r} (delta {float(a)-float(b):.3e})")
        elif a != b:
            bad.append(f"{k}: {a!r} != committed {b!r}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=6)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    out = args.out
    if out.resolve() == COMMITTED.resolve():
        raise SystemExit(f"refusing to overwrite {COMMITTED} -- it is the gate and the "
                         f"headline. Pass a different --out.")

    head = _head()
    gate = _load_gate(COMMITTED)
    print(f"Version B · two-plate SPADE · HEAD={head}")
    print(f"{N_PLATE1} + {N_PLATE2} = {N_PLATE1+N_PLATE2} wells · LSE targets "
          f"tau_frac={DESIGN_TAU_FRAC} · rounds {ROUNDS}")
    print(f"out={out} · gate={COMMITTED} ({len(gate)} rows) · acq_cv flat below "
          f"{ACQ_CV_FLAT}\n")

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == args.dim and r["sigma"] == args.sigma
                   and r["arm"] == "qlogei"})
    if args.limit: keys = keys[:args.limit]
    print(f"{len(keys)} instance-seeds\n")

    grid = sobol_grid(args.dim, GRID_N, seed=GRID_SEED)
    X_sub = sobol_grid(args.dim, SUBSET_N, seed=GRID_SEED)
    rows, gate_failures, n_gated, t0 = [], [], 0, time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, args.dim)
        orc_t = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
        with torch.no_grad():
            truth = orc_t.truth(grid).reshape(-1).double()
            truth_sub = orc_t.truth(X_sub).reshape(-1).double()
        mu_max = float(inst.optimum_value)

        for arm in ARMS:
            t = time.time()
            kept = held = None
            diag = {}
            orc = BiphasicOracle(inst, sigma_rel=args.sigma, seed=seed)
            if arm.startswith("versionb"):
                mode = {"versionb": "lse", "versionb_random": "random",
                        "versionb_predictive": "predictive"}[arm]
                X, Y, V, diag = _two_plate(orc, args.dim, seed, mu_max, mode)
            elif arm == "plate1_only":
                X = static_design(unit_bounds(args.dim), "lhs", BUDGET, seed)
                Y, V = orc.evaluate(X)
            else:
                rec = regenerate(inst_id, args.dim, args.sigma, seed, arm)
                X, Y, V = rec.X, rec.Y, rec.Yvar
                kept, held = rec.kept_factors, rec.dropped_held_at
            if arm != "doe":
                kept = held = None
            r = _score(X, Y, V, orc_t, args.dim, mu_max, grid, truth, X_sub, truth_sub,
                       seed, kept=kept, held=held)
            r.update(diag)
            r.update({"instance": inst_id, "seed": seed, "arm": arm,
                      "rounds": ROUNDS[arm], "dim": args.dim, "sigma": args.sigma})

            ref = gate.get((inst_id, seed, arm))
            bad = _gate(r, ref)
            n_gated += ref is not None
            if bad:
                gate_failures.append({"instance": inst_id, "seed": seed, "arm": arm,
                                      "failures": bad})
                print(f"\nGATE FAILURE {arm} {inst_id} seed={seed}:")
                for b in bad[:8]:
                    print(f"    {b}")
                raise SystemExit("a regenerated campaign missed its committed column; "
                                 "stopping rather than absorbing it")

            rows.append(r)
            cv = r.get("acq_cv")
            cvs = "     -   " if cv is None else f"cv={cv:6.3f}"
            mc = r.get("plate2_min_cheb")
            mcs = "        " if mc is None else f"d2={mc:.3f}"
            print(f"[{i:3d}/{len(keys)}] {arm:20s} {inst_id} seed={seed} "
                  f"n={r['n_wells']} regret={r['regret']:.4f} "
                  f"a*={r[f'alpha_star_{DESIGN_TAU_FRAC}']:.3f} {cvs} {mcs} "
                  f"{'GATED' if ref is not None else '  new'} ({time.time()-t:.1f}s)",
                  flush=True)

        out.write_text(json.dumps({
            "provenance": {"git_sha": head, "argv": sys.argv,
                           "python": platform.python_version(),
                           "gate_file": str(COMMITTED), "gate_rows_checked": n_gated,
                           "gate_failures": gate_failures},
            "config": {"dim": args.dim, "sigma": args.sigma,
                       "n_plate1": N_PLATE1, "n_plate2": N_PLATE2,
                       "tau_fracs": list(TAU_FRACS),
                       "design_tau_frac": DESIGN_TAU_FRAC, "rounds": ROUNDS,
                       "arms": list(ARMS), "alphas": list(ALPHAS),
                       "grid_n": GRID_N, "subset_n": SUBSET_N, "cand_n": CAND_N,
                       "n_draws": N_DRAWS, "acq_cv_flat": ACQ_CV_FLAT},
            "rows": rows}, indent=2))
        del truth, truth_sub; gc.collect()

    print(f"\n{len(rows)} rows in {time.time()-t0:.0f}s · "
          f"{n_gated} gated comparisons, {len(gate_failures)} failures")
    flat = [r for r in rows if r.get("acq_flat")]
    lse_rows = [r for r in rows if r.get("acq_cv") is not None]
    print(f"acq_cv over {len(lse_rows)} LSE-arm campaigns: "
          f"below {ACQ_CV_FLAT} in {len(flat)}")
    bound = [r for r in rows if r.get("excl_bound")]
    print(f"exclusion bound in {len(bound)}/{len(lse_rows)} LSE-arm campaigns")


if __name__ == "__main__":
    main()
