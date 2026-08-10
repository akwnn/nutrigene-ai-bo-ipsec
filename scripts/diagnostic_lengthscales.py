"""Why did BO lose at d=6? Read the fitted lengthscales against a no-signal null.

OWNERSHIP: Person A. **DIAGNOSTIC. CHANGES NO E2 NUMBER.**

Run with::

    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/diagnostic_lengthscales.py

------------------------------------------------------------------------------
VERSION 2. WHAT VERSION 1 GOT WRONG.
------------------------------------------------------------------------------

Version 1 compared fitted lengthscales against the prior MEDIAN, exp(loc) = 10.08
at d=6, and concluded from "0.435, twenty-three times below it" that the data had
won. **That comparison was void.** The fit is MAP, so its no-data attractor is the
prior MODE, exp(loc - scale**2) = 0.5016 -- which is also gpytorch's kernel
initialisation, and is exactly what a 14-point fit on signal-free outcomes
returns. Version 1's opening-design median was 0.502. It read a model that had
learned nothing as a model that had learned everything.

Three things change here, and all three are corrections to fidelity rather than
to the question being asked:

  1. **An empirical no-signal null replaces the closed-form anchor.** At every
     checkpoint the same design and the same noise are refit with the outcome
     vector PERMUTED. Anything the real fit does that the permuted fit does not
     is signal. No formula can substitute: with n points present the likelihood
     always moves the fit somewhere, and how far it moves on noise alone depends
     on n, the design and the noise level.

  2. **Every checkpoint is now a model the campaign actually built.** Version 1
     used n = 31/33 (mid-batch, a training set that never existed, and a
     different n in each dimension) and n = 48 (post-terminal -- `Campaign.run`
     fits before each `ask` and never after the final `tell`, so the last model
     it ever built saw 46 points). The checkpoints are now the opening design,
     n=30 and n=46, all three real round boundaries at BOTH dimensions.

  3. **The "these are E2's runs" claim is asserted, not promised.** Each row
     recomputes the arm's scored best and checks it against the stored
     `results/e2-grid.json` row for the same (dim, sigma, instance, seed). A
     mismatch fails the run loudly instead of quietly polluting a median.

Lengthscales are split active/inert using each instance's OWN `active_mask` --
the four active factors are not the first four, so pooling by index would average
the two groups together. Medians and IQRs throughout; lengthscales are
heavy-tailed.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")   # before numpy/torch, not after

import hashlib                                   # noqa: E402
import json                                      # noqa: E402
from multiprocessing import Pool                 # noqa: E402
from pathlib import Path                         # noqa: E402

import numpy as np                               # noqa: E402

BUDGET = 48
N_INSTANCES = 25          # E2's grid exactly. Not the 40 available at d=6.
N_SEEDS = 2
CELLS = [(6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10)]
AT_BOUND = 1e-3           # coded units
N_PERM = 3                # permutation draws per checkpoint
FIDELITY_TOL = 1e-9

# Real round boundaries at BOTH dimensions. batch_plan(6,48,4) fits at
# 14,18,...,46 and batch_plan(8,48,4) at 18,22,...,46, so 30 and 46 are shared.
MID, FINAL = 30, 46


def _e2_reference() -> dict:
    """Stored E2 qLogEI results, keyed for the fidelity assertion."""
    rows = json.loads(Path("results/e2-grid.json").read_text())
    return {(r["dim"], r["sigma"], r["instance"], r["seed"]): r["best"]
            for r in rows if r["arm"] == "qlogei"}


def _row(task: tuple[int, float, int, int]) -> dict:
    """One (dim, sigma, instance, seed). Imports inside for a spawned worker."""
    import torch

    torch.set_num_threads(1)

    from botorch.acquisition.analytic import PosteriorMean
    from botorch.optim import optimize_acqf

    from boec.campaign import Campaign, CampaignConfig, batch_plan
    from boec.diagnostics import reported_best_curve
    from boec.lengthscale_diag import (
        censored_fwhm,
        fraction_at_floor,
        permutation_null_lengthscales,
        prior_band_fraction,
        prior_loc_scale,
        prior_mode,
    )
    from boec.optimizers import AcqConfig
    from boec.oracles import HillOracle, load_ensemble
    from boec.surrogate import (
        build_gp,
        lengthscale_lower_bound,
        lengthscales,
        predictive,
    )
    from boec.torch_oracle import BiphasicOracle

    dim, sigma, i_inst, seed = task
    inst = load_ensemble(dim=dim)[i_inst]
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])

    # --- regenerate the campaign E2 ran, purely to recover its design matrix ---
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cfg = CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed,
                         acq=AcqConfig(kind="qlogei"))
    camp = Campaign(orc, bounds, cfg).run()
    n_init, _ = batch_plan(dim, BUDGET, 4)

    mask = np.asarray(inst.active_mask, dtype=bool)
    hill = HillOracle(inst)
    x_opt = np.asarray(inst.optimum_x, dtype=float)
    fwhm = censored_fwhm(inst)

    out: dict = dict(
        dim=dim, sigma=sigma, instance=inst.instance_id, seed=seed,
        n_init=n_init, n_active=int(mask.sum()),
        # the fidelity assertion's payload -- exactly run_e2.scored_curve
        best=float(reported_best_curve(orc.truth(camp.train_X), camp.train_Y)[-1]),
        # `best` is a max over a curve, so two different designs can share it.
        # The hash closes that gap: it pins the DESIGN, not just its score.
        x_hash=hashlib.sha256(
            np.ascontiguousarray(
                camp.train_X.detach().double().cpu().numpy()).tobytes()
        ).hexdigest()[:16],
        fwhm_active=fwhm[mask].tolist(),
        fwhm_inert=fwhm[~mask].tolist(),
        true_opt_coords_at_bound=int(
            np.sum(np.minimum(x_opt, 1.0 - x_opt) < AT_BOUND)),
        checkpoints={},
    )

    # --- 2.1  fitted lengthscales vs the no-signal null, at three real rounds --
    final = None
    for tag, n in (("init", n_init), ("mid", MID), ("final", FINAL)):
        model = build_gp(camp.train_X[:n], camp.train_Y[:n],
                         camp.train_Yvar[:n], bounds)
        ls = lengthscales(model).detach().double().cpu().numpy().ravel()
        null = permutation_null_lengthscales(
            camp.train_X[:n], camp.train_Y[:n], camp.train_Yvar[:n], bounds,
            n_perm=N_PERM, seed=seed)
        loc, scale = prior_loc_scale(model)
        lb = lengthscale_lower_bound(model)
        out["checkpoints"][tag] = dict(
            n=n,
            ls_active=ls[mask].tolist(),
            ls_inert=ls[~mask].tolist(),
            null_active=null[:, mask].ravel().tolist(),
            null_inert=null[:, ~mask].ravel().tolist(),
            prior_loc=loc, prior_scale=scale,
            prior_median=float(np.exp(loc)),
            prior_mode=prior_mode(model),
            lower_bound=lb,
            band_active=prior_band_fraction(ls[mask], loc, scale),
            floor_all=fraction_at_floor(ls, lb),
            ratio_ls_over_fwhm_active=(ls[mask] / fwhm[mask]).tolist(),
        )
        if tag == "final":
            final = model

    # --- 2.3  did it cost anything?  On n=46: the model that chose the last batch
    #
    # RAW SLICE RMSE IS NOT USABLE AND IS NOT REPORTED. It decomposes exactly into
    # a level term and a shape term, the level term dominates by ~35x in variance
    # because x_opt sits far from any design point, and the true slice variation
    # scales with that coordinate's WEIGHT -- so the active/inert RMSE ordering is
    # fixed by the sampler's active_share=0.90 and comes out identically in the
    # cell where BO wins and the cell where it loses. Reported instead:
    #   level_j  = |mean residual|      -- how far off the GP's level is
    #   shape_j  = sd of the residual   -- how much of the CURVE it missed
    #   skill_j  = 1 - shape_j^2 / var(truth along the slice)
    # skill has a principled zero (a shape-blind predictor scores 0) and is
    # scale-free, so active and inert are comparable and so are d=6 and d=8.
    grid = np.union1d(np.linspace(0.0, 1.0, 33), x_opt)   # always evaluate the peak
    level = np.empty(dim)
    shape = np.empty(dim)
    skill = np.empty(dim)
    for j in range(dim):
        Xs = np.tile(x_opt, (grid.size, 1))
        Xs[:, j] = grid
        truth = hill.f(Xs)
        mu = predictive(final, torch.as_tensor(Xs, dtype=torch.double)
                        ).mean.detach().double().cpu().numpy().ravel()
        res = mu - truth
        level[j] = float(abs(res.mean()))
        shape[j] = float(res.std())
        v = float(truth.var())
        skill[j] = float(1.0 - shape[j] ** 2 / v) if v > 0 else float("nan")
    for name, arr in (("level", level), ("shape", shape), ("skill", skill)):
        out[f"slice_{name}_active"] = arr[mask].tolist()
        out[f"slice_{name}_inert"] = arr[~mask].tolist()
    # coverage context: the level term is only interpretable knowing how far the
    # slice sits from any training point
    Xtr = camp.train_X[:FINAL].detach().double().cpu().numpy()
    out["dist_xopt_to_nearest_train"] = float(
        np.min(np.linalg.norm(Xtr - x_opt, axis=1)))

    def _argmax_of(model):
        xh, _ = optimize_acqf(PosteriorMean(model), bounds=bounds, q=1,
                              num_restarts=10, raw_samples=256)
        xh = xh.detach().double().cpu().numpy().ravel()
        return xh, np.minimum(xh, 1.0 - xh)

    xh, face = _argmax_of(final)
    out["post_mean_argmax_interior"] = bool(not (face < AT_BOUND).any())
    out["post_mean_argmax_face_dist"] = float(face.min())   # continuous, not binary
    out["post_mean_argmax_err"] = float(np.linalg.norm(xh - x_opt))
    out["post_mean_argmax_err_active"] = float(
        np.linalg.norm((xh - x_opt)[mask]) / np.sqrt(mask.sum()))
    out["post_mean_at_bound_active"] = int((face[mask] < AT_BOUND).sum())
    out["post_mean_at_bound_inert"] = int((face[~mask] < AT_BOUND).sum())

    # --- THE COUNTERFACTUAL: same recovered design, Gamma(3,6) lengthscale prior
    # No campaign is re-run and no E2 number is touched. Without a condition that
    # varies the prior, no lengthscale value can attribute anything TO the prior;
    # this is the cheapest arm that can.
    cf = build_gp(camp.train_X[:FINAL], camp.train_Y[:FINAL],
                  camp.train_Yvar[:FINAL], bounds, lengthscale_prior="gamma")
    cf_ls = lengthscales(cf).detach().double().cpu().numpy().ravel()
    cf_xh, cf_face = _argmax_of(cf)
    out["cf_gamma"] = dict(
        ls_active=cf_ls[mask].tolist(),
        ls_inert=cf_ls[~mask].tolist(),
        argmax_err=float(np.linalg.norm(cf_xh - x_opt)),
        argmax_err_active=float(
            np.linalg.norm((cf_xh - x_opt)[mask]) / np.sqrt(mask.sum())),
        argmax_interior=bool(not (cf_face < AT_BOUND).any()),
    )

    Xa = camp.train_X[n_init:].detach().double().cpu().numpy()
    half = Xa.shape[0] // 2
    # per-coordinate RMS, so d=6 and d=8 are on the same scale, and on the ACTIVE
    # subspace, because full-space distance is mostly contributed by coordinates
    # BO is right to ignore
    dact = np.linalg.norm((Xa - x_opt)[:, mask], axis=1) / np.sqrt(mask.sum())
    dfull = np.linalg.norm(Xa - x_opt, axis=1) / np.sqrt(dim)
    out["prop_dist_active_first"] = float(np.median(dact[:half]))
    out["prop_dist_active_second"] = float(np.median(dact[half:]))
    out["prop_dist_full_first"] = float(np.median(dfull[:half]))
    out["prop_dist_full_second"] = float(np.median(dfull[half:]))
    prop_at_bound = np.minimum(Xa, 1.0 - Xa) < AT_BOUND
    out["prop_frac_any_coord_at_bound"] = float(np.mean(prop_at_bound.any(axis=1)))
    out["prop_frac_coords_at_bound_active"] = float(prop_at_bound[:, mask].mean())
    out["prop_frac_coords_at_bound_inert"] = float(prop_at_bound[:, ~mask].mean())

    # uniform null, on the same per-coordinate RMS scale
    rng = np.random.default_rng(12345 + i_inst)
    U = rng.random((4000, dim))
    out["null_dist_active"] = float(np.median(
        np.linalg.norm((U - x_opt)[:, mask], axis=1) / np.sqrt(mask.sum())))
    out["null_dist_full"] = float(np.median(
        np.linalg.norm(U - x_opt, axis=1) / np.sqrt(dim)))
    out["xopt_margin_to_face"] = float(np.min(np.minimum(x_opt, 1.0 - x_opt)))
    return out


def _q(v):
    v = np.asarray(v, dtype=float)
    return np.median(v), np.percentile(v, 25), np.percentile(v, 75)


def _flat(rows, key, tag=None):
    if tag is None:
        return np.array([x for r in rows for x in np.atleast_1d(r[key])], dtype=float)
    return np.array([x for r in rows for x in r["checkpoints"][tag][key]], dtype=float)


def report(rows: list[dict]) -> None:
    from scipy.stats import wilcoxon

    def cell(d, sg):
        return [r for r in rows if r["dim"] == d and r["sigma"] == sg]

    def per_run(sub, tag, key):
        """One number per run: the run's median over that coordinate group."""
        return np.array([np.median(r["checkpoints"][tag][key]) for r in sub])

    def log_ratio_by_instance(sub, tag, src):
        """Clustered on instance, in log space. Both corrections, one place.

        Version 2 of this report ran its Wilcoxon over all 50 RUNS. `e2.yaml`
        registers `cluster: instance` and 25 landscapes x 2 seeds has effective
        n = 25 -- so that was pseudo-replication, the very error this project
        criticises the source paper for. And a signed-RANK test on a difference
        of RATIOS is anti-conservative, because the null differences are
        right-skewed: measured 8.9% at a nominal 5%. Log space fixes the second,
        averaging seeds within a landscape fixes the first.
        """
        insts = sorted({r["instance"] for r in sub})
        out = []
        for i in insts:
            rs = [r for r in sub if r["instance"] == i]
            out.append(np.mean([
                np.log(np.median(r["checkpoints"][tag][f"{src}_inert"]) /
                       np.median(r["checkpoints"][tag][f"{src}_active"])) for r in rs]))
        return np.array(out)

    def med_iqr(v):
        v = np.asarray(v, float)
        return f"{np.median(v):.3f} [{np.percentile(v, 25):.3f},{np.percentile(v, 75):.3f}]"

    print("\nPROPERTIES OF THE PRIOR AND THE ENSEMBLE (fit-independent — not results)")
    for dim in (6, 8):
        c = [r for r in cell(dim, 0.25)]
        if not c:
            continue
        cp = c[0]["checkpoints"]["final"]
        w = np.median(_flat(c, "fwhm_active"))
        print(f"  d={dim}: prior median {cp['prior_median']:.2f}  |  prior MODE "
              f"{cp['prior_mode']:.4f} = the MAP attractor AND the kernel's "
              f"initialisation  |  lengthscale floor {cp['lower_bound']:g}")
        print(f"        true active feature width (censored FWHM) {w:.3f}; "
              f"prior mode / width {cp['prior_mode'] / w:.2f}")
    print("  Version 1 anchored on the MEDIAN. That was void: a fit that has learned")
    print("  nothing sits at the MODE, which v1 scored as maximal learning.")

    print("\n" + "=" * 100)
    print("2.1  ARD SEPARATION vs ITS OWN NO-SIGNAL NULL   <-- THE DECIDING STATISTIC")
    print("=" * 100)
    _pooled_null = np.concatenate([
        per_run(cell(d, sg), "final", "null_inert") /
        per_run(cell(d, sg), "final", "null_active")
        for d, sg in CELLS if cell(d, sg)])
    print("The prior is identical on every dimension, so ANY uninformed fit — prior-")
    print("dominated, badly initialised, whatever — gives inert/active = 1.00 by")
    print(f"symmetry. Measured on permuted outcomes, pooled over all cells at n=46: "
          f"{np.median(_pooled_null):.3f}.")
    print("Anything above that is data-driven discrimination and cannot be an artefact")
    print("of the anchoring error that voided version 1.\n")
    print(f"{'cell':>13} {'stage':>6} {'n':>3} {'FIT inert/active':>24} "
          f"{'NULL inert/active':>24} {'p(fit>null)':>12}")
    for dim, sigma in CELLS:
        sub = cell(dim, sigma)
        if not sub:
            continue
        star = "  <-- primary" if (dim, sigma) == (6, 0.25) else ""
        for tag in ("init", "mid", "final"):
            fr = np.exp(log_ratio_by_instance(sub, tag, "ls"))
            nr = np.exp(log_ratio_by_instance(sub, tag, "null"))
            p = wilcoxon(log_ratio_by_instance(sub, tag, "ls")
                         - log_ratio_by_instance(sub, tag, "null"),
                         alternative="greater").pvalue
            print(f"{f'd={dim} s={sigma}':>13} {tag:>6} "
                  f"{sub[0]['checkpoints'][tag]['n']:>3} "
                  f"{med_iqr(fr):>24} {med_iqr(nr):>24} {p:>12.2e}"
                  + (star if tag == "final" else ""))

    print("\n" + "=" * 100)
    print("2.2  LENGTHSCALE LEVELS, and what a no-signal fit on the same design gives")
    print("=" * 100)
    print(f"{'cell':>13} {'stage':>6} {'ACTIVE fit':>22} {'ACTIVE null':>22} "
          f"{'INERT fit':>22} {'INERT null':>22}")
    for dim, sigma in CELLS:
        sub = cell(dim, sigma)
        if not sub:
            continue
        for tag in ("init", "final"):
            print(f"{f'd={dim} s={sigma}':>13} {tag:>6} "
                  f"{med_iqr(per_run(sub, tag, 'ls_active')):>22} "
                  f"{med_iqr(per_run(sub, tag, 'null_active')):>22} "
                  f"{med_iqr(per_run(sub, tag, 'ls_inert')):>22} "
                  f"{med_iqr(per_run(sub, tag, 'null_inert')):>22}")
    print("\n  Read the LEVELS with care — they are the part version 1 got wrong.")
    print("  Learning does NOT mean 'shorter': on an active factor the right")
    print("  lengthscale is near the feature width, which is close to where the MAP")
    print("  attractor already sits, so the level barely has to move. On an inert")
    print("  factor the right lengthscale is LONG. That is why 2.1 decides and not this.")

    print("\n" + "=" * 100)
    print("2.3  DID IT COST ANYTHING?  (n=46, the model that chose the final batch)")
    print("=" * 100)
    print("  SHAPE SKILL = 1 - var(residual)/var(truth) along a slice through the true")
    print("  optimum. A shape-blind predictor scores 0 whatever its level error, so")
    print("  active and inert are comparable and so are d=6 and d=8. Raw slice RMSE is")
    print("  NOT reported: it is ~97% level error and its active/inert ordering is")
    print("  fixed by the oracle's weights, identical in the winning and losing cells.")
    print("  CAVEAT: skill on INERT coordinates has a near-zero denominator by")
    print("  construction — the truth is almost flat there — so it goes large and")
    print("  negative and is NOT comparable to the active column. Only the ACTIVE")
    print("  column is interpretable as a skill; the inert one is reported for")
    print("  completeness and should be read as 'the GP moves where the truth does not'.\n")
    print(f"{'cell':>13} {'skill act':>22} {'skill inert':>22} {'level err':>10} "
          f"{'x_opt->train':>13}")
    for dim, sigma in CELLS:
        sub = cell(dim, sigma)
        if not sub:
            continue
        print(f"{f'd={dim} s={sigma}':>13} "
              f"{med_iqr(_flat(sub, 'slice_skill_active')):>22} "
              f"{med_iqr(_flat(sub, 'slice_skill_inert')):>22} "
              f"{np.median(_flat(sub, 'slice_level_active')):>10.4f} "
              f"{np.median([r['dist_xopt_to_nearest_train'] for r in sub]):>13.4f}")

    print(f"\n{'cell':>13} {'|argmax-opt| act':>18} {'null':>8} {'CF gamma':>9} | "
          f"{'proposals: act 1st':>19} {'2nd':>8} {'null':>8} | {'@bound act':>11} "
          f"{'@bound inert':>13}")
    for dim, sigma in CELLS:
        sub = cell(dim, sigma)
        if not sub:
            continue
        print(f"{f'd={dim} s={sigma}':>13} "
              f"{np.median([r['post_mean_argmax_err_active'] for r in sub]):>18.4f} "
              f"{np.median([r['null_dist_active'] for r in sub]):>8.4f} "
              f"{np.median([r['cf_gamma']['argmax_err_active'] for r in sub]):>9.4f} | "
              f"{np.median([r['prop_dist_active_first'] for r in sub]):>19.4f} "
              f"{np.median([r['prop_dist_active_second'] for r in sub]):>8.4f} "
              f"{np.median([r['null_dist_active'] for r in sub]):>8.4f} | "
              f"{np.mean([r['prop_frac_coords_at_bound_active'] for r in sub]):>11.3f} "
              f"{np.mean([r['prop_frac_coords_at_bound_inert'] for r in sub]):>13.3f}")
    print("\n  All distances are per-coordinate RMS on the ACTIVE subspace, so d=6 and")
    print("  d=8 are comparable and the nuisance coordinates BO is right to ignore do")
    print("  not dilute the signal. 'null' = a uniform random point in the box.")
    print("  '@bound' is the fraction of proposed COORDINATE VALUES on a face, split by")
    print("  group: an inert coordinate on a bound is near-costless by the oracle's own")
    print("  design and must not be pooled with an active one. No uniform reference is")
    print("  quoted — qLogEI is a bounded maximiser of an acquisition whose exploration")
    print("  term peaks at faces, so a uniform draw is not its operative null.")

    print("\n" + "=" * 100)
    print("2.4  COUNTERFACTUAL: the same recovered designs, Gamma(3,6) lengthscale prior")
    print("=" * 100)
    print("  No campaign is re-run and no E2 number is touched. Without a condition")
    print("  that varies the prior, no lengthscale value can attribute anything TO the")
    print("  prior. Gamma(3,6) penalises ls=10 by ~51 nats/dim where the shipped prior")
    print("  penalises it by ~1.5, so this isolates the tail penalty; their modes are")
    print("  0.502 and 0.333, nearly the same place.\n")
    print(f"{'cell':>13} {'shipped act':>22} {'gamma act':>22} "
          f"{'shipped in/act':>16} {'gamma in/act':>14} {'p':>10}")
    for dim, sigma in CELLS:
        sub = cell(dim, sigma)
        if not sub:
            continue
        sa = per_run(sub, "final", "ls_active")
        si = per_run(sub, "final", "ls_inert")
        ga = np.array([np.median(r["cf_gamma"]["ls_active"]) for r in sub])
        gi = np.array([np.median(r["cf_gamma"]["ls_inert"]) for r in sub])
        p = wilcoxon(si / sa - gi / ga).pvalue
        print(f"{f'd={dim} s={sigma}':>13} {med_iqr(sa):>22} {med_iqr(ga):>22} "
              f"{np.median(si / sa):>16.2f} {np.median(gi / ga):>14.2f} {p:>10.2e}")

    floor = np.mean([r["checkpoints"]["final"]["floor_all"] for r in rows])
    margin = min(r["xopt_margin_to_face"] for r in rows)
    print(f"\n  controls: lengthscales pinned to the floor = {floor:.3f}. The true")
    print(f"  optimum's closest approach to any face, over all {len(rows)} runs, is "
          f"{margin:.3f} —")
    print("  the ensemble's xstar range makes a boundary optimum impossible, so that")
    print("  control could not have failed and is reported as a margin, not a pass.")


def main() -> None:
    ref = _e2_reference()
    tasks = [(dim, sigma, i, s)
             for dim, sigma in CELLS
             for i in range(N_INSTANCES)
             for s in range(N_SEEDS)]
    print(f"{len(tasks)} qLogEI campaigns to regenerate, 7 workers", flush=True)
    rows = []
    with Pool(7) as pool:
        for k, r in enumerate(pool.imap_unordered(_row, tasks), 1):
            rows.append(r)
            if k % 25 == 0:
                print(f"  {k}/{len(tasks)}", flush=True)

    # --- FIDELITY: these must be the runs E2 scored, or nothing below applies ---
    bad = []
    for r in rows:
        key = (r["dim"], r["sigma"], r["instance"], r["seed"])
        if key not in ref:
            bad.append((key, "absent from results/e2-grid.json", None))
        elif abs(r["best"] - ref[key]) > FIDELITY_TOL:
            bad.append((key, r["best"], ref[key]))
    if bad:
        for b in bad[:10]:
            print(f"  FIDELITY MISMATCH {b}")
        raise SystemExit(
            f"{len(bad)}/{len(rows)} regenerated campaigns do not reproduce their "
            "stored E2 result. Every number below would describe runs E2 never ran."
        )
    print(f"\nFIDELITY: {len(rows)}/{len(rows)} regenerated campaigns reproduce their "
          f"stored E2 `best` to within {FIDELITY_TOL:g}.")

    Path("results").mkdir(exist_ok=True)
    Path("results/diagnostic-lengthscales.json").write_text(json.dumps(rows, indent=1))
    report(rows)


if __name__ == "__main__":
    main()
