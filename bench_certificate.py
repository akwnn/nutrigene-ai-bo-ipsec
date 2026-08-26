"""Isolate the SPADE certificate stage: fixed Sobol-48 data, production code paths.

The campaign design is held fixed across variants so any change in containment is
attributable to the certificate rule, not to which points were evaluated.
"""
from __future__ import annotations

import argparse, json, statistics, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import torch
from boec.reliable_region import (
    conservative_set_split, empirical_set_containment, model_reliability_probability,
    reliable_set_draws, true_reliability_probability,
)
from boec.reliable_region import clopper_pearson_lower
from boec.seedbook import derive_seed
from boec.selfcalib import calibration_inflation, loo_residuals


def loo_kappa(model) -> float:
    """Per-campaign overconfidence factor from the campaign's own LOO residuals.

    Joseph's Route B (selfcalib), evaluated in the model's transformed space so the
    noise-inclusive covariance and the targets agree.
    """
    import numpy as np
    Xtr = model.train_inputs[0].detach().double()
    ytr = model.train_targets.detach().double().reshape(-1)
    with torch.no_grad():
        K = model.covar_module(Xtr).to_dense().double()
        noise = model.likelihood.noise.detach().double().reshape(-1)[0]
        K = K + noise * torch.eye(K.shape[0], dtype=torch.double)
    mu, var = loo_residuals(K.numpy(), ytr.numpy())
    return float(calibration_inflation(ytr.numpy(), mu, np.sqrt(var)))
from boec.spade_study import ScoringExecutionSettings, sobol_grid
from boec.surrogate import build_learned_noise_gp

import run_spade_development as RSD
from scipy.stats import norm


def reliability_contour(tau, gamma, sigma_rel, sigma_add):
    """Latent theta with P(Y >= tau | f=theta) == gamma, under relative+additive noise."""
    z = float(norm.ppf(gamma))
    a = 1.0 - z * z * sigma_rel ** 2
    b = -2.0 * tau
    c = tau * tau - z * z * sigma_add ** 2
    disc = b * b - 4 * a * c
    if disc < 0 or a == 0:
        return tau + z * sigma_add
    r1 = (-b + disc ** 0.5) / (2 * a)
    r2 = (-b - disc ** 0.5) / (2 * a)
    roots = [r for r in (r1, r2) if r >= tau - 1e-12]
    return min(roots) if roots else max(r1, r2)


def straddle_design(evaluator, tau, key, family, *, opening, rounds, batch,
                    rho, fit_restarts, pool=4096):
    """SPADE-shaped design that spends adaptive budget on the certificate contour.

    score = 1.96*sd - |mean - Phi^-1(rho)*sd - theta|, i.e. Bryan's straddle displaced
    onto the contour that actually bounds the certified region (rho > 0.5).
    """
    theta = reliability_contour(tau, GAMMA, SIGMA_REL, SIGMA_ADD)
    zr = float(norm.ppf(rho))
    X = sobol_grid(DIM, opening, derive_seed(key, "bench_design", family))
    Y = evaluator.evaluate(X)[0].reshape(-1, 1).double()
    for r in range(rounds):
        model = _fit(X, Y, derive_seed(key, f"bench_adapt{r}", family), fit_restarts)
        cand = sobol_grid(DIM, pool, derive_seed(key, f"bench_pool{r}", family))
        _, mean, var = _latent_posterior(model, cand)
        sd = var.clamp_min(1e-12).sqrt()
        score = 1.96 * sd - (mean - zr * sd - theta).abs()
        picked = []
        order = torch.argsort(score, descending=True)
        for i in order.tolist():
            x = cand[i]
            if any(float((x - X[j]).norm()) < 1e-6 for j in range(X.shape[0])):
                continue
            if any(float((x - cand[j]).norm()) < 0.05 for j in picked):
                continue
            picked.append(i)
            if len(picked) == batch:
                break
        newX = cand[picked]
        newY = evaluator.evaluate(newX)[0].reshape(-1, 1).double()
        X = torch.cat([X, newX], dim=0)
        Y = torch.cat([Y, newY], dim=0)
    return X, Y
from boec.reliable_region import _latent_posterior, _standard_normal_cdf


def inflated_set_draws(model, X, tau, gamma, n_draws, seed, *, kappa,
                       sigma_rel, sigma_add):
    """reliable_set_draws with the joint latent draws' spread scaled by kappa >= 1."""
    posterior, mean, _ = _latent_posterior(model, X)
    base_shape = torch.Size(posterior.base_sample_shape)
    g = torch.Generator(device="cpu"); g.manual_seed(int(seed))
    base = torch.randn(torch.Size([n_draws]) + base_shape, generator=g,
                       dtype=torch.double).to(dtype=mean.dtype)
    with torch.no_grad():
        latent = posterior.rsample_from_base_samples(torch.Size([n_draws]), base)
    latent = latent.squeeze(-1).double()
    latent = mean.double().unsqueeze(0) + kappa * (latent - mean.double().unsqueeze(0))
    nv = sigma_rel ** 2 * latent.square() + sigma_add ** 2
    prob = 1.0 - _standard_normal_cdf((tau - latent) / nv.sqrt())
    return prob >= gamma

SIGMA_REL, SIGMA_ADD, GAMMA, ALPHA = RSD._SIGMA_REL, RSD._SIGMA_ADD, RSD._GAMMA, RSD._ALPHA
DIM, BUDGET = 6, 48


def _fit(X, Y, seed, fit_restarts):
    bounds = torch.stack([torch.zeros(DIM, dtype=torch.double),
                          torch.ones(DIM, dtype=torch.double)])
    return build_learned_noise_gp(X.clone(), Y.clone(), bounds,
                                  fit_restarts=fit_restarts, seed=seed)


def _ensemble_draws(X, Y, grid, tau, draws, members, base_seed, fit_restarts, family, key):
    """Set draws marginalized over estimation uncertainty via a bootstrap GP ensemble.

    Each member refits hyperparameters on a resample of the campaign observations, so
    the draw distribution carries plug-in uncertainty the single-fit path cannot see.
    """
    per = draws // members
    if per % 2:
        per -= 1
    rows = []
    n = X.shape[0]
    for m in range(members):
        g = torch.Generator().manual_seed(derive_seed(key, f"bench_boot{m}", family) % (2**31))
        idx = torch.randint(0, n, (n,), generator=g)
        model_m = _fit(X[idx], Y[idx], derive_seed(key, f"bench_bootfit{m}", family), fit_restarts)
        rows.append(reliable_set_draws(
            model_m, grid, tau, GAMMA, per,
            derive_seed(key, f"bench_bootdraw{m}", family),
            sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD))
    return torch.cat(rows, dim=0)


def one_key(family: str, key: int, *, cert_grid: int, draws: int, n_rho: int,
            alpha: float, volume_rule: str, fit_restarts: int = 4, budget: int = BUDGET,
            members: int = 1, kappa: float = 1.0, loo_scale: float = 0.0,
            design: str = "sobol", rho: float = 0.5):
    """One instance: fit the terminal GP on Sobol-48 data, then certify."""
    harness, threshold = RSD._development_threshold(
        family,
        key % len(RSD.HILL_DEVELOPMENT_INSTANCE_IDS) if family == "hill" else key,
        derive_seed(key, "bench_noise", family),
        derive_seed(key, "bench_threshold", family),
        smoke=False,
    )
    tau = threshold.tau
    _, evaluator, _ = RSD._development_oracle(
        family,
        key % len(RSD.HILL_DEVELOPMENT_INSTANCE_IDS) if family == "hill" else key,
        derive_seed(key, "bench_noise", family),
    )
    scorer = harness.scorer()

    if design == "straddle":
        X, Y = straddle_design(evaluator, tau, key, family, opening=32, rounds=4,
                               batch=4, rho=rho, fit_restarts=fit_restarts)
    else:
        X = sobol_grid(DIM, budget, derive_seed(key, "bench_design", family))
        Y = evaluator.evaluate(X)[0].reshape(budget, 1).double()

    grid = sobol_grid(DIM, cert_grid, derive_seed(key, "bench_cert_grid", family))
    model_for_map = _fit(X, Y, derive_seed(key, "bench_fit", family), fit_restarts)
    if members > 1:
        set_draws = _ensemble_draws(X, Y, grid, tau, draws, members,
                                    derive_seed(key, "bench_draws", family),
                                    fit_restarts, family, key)
    else:
        model = model_for_map
        if loo_scale > 0.0:
            kappa = max(loo_kappa(model), 1.0) * loo_scale
        if kappa != 1.0:
            set_draws = inflated_set_draws(
                model, grid, tau, GAMMA, draws,
                derive_seed(key, "bench_draws", family), kappa=kappa,
                sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD)
        else:
            set_draws = reliable_set_draws(
                model, grid, tau, GAMMA, draws, derive_seed(key, "bench_draws", family),
                sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD,
            )
    cert = conservative_set_split(set_draws, alpha, n_rho=n_rho, volume_rule=volume_rule)

    truth = scorer._truth(grid)
    true_mask = true_reliability_probability(truth, tau, SIGMA_REL, SIGMA_ADD) >= GAMMA
    empirical = empirical_set_containment(cert.mask, true_mask)

    # Does the posterior MEAN put the reliable region in the right place at all?
    pmap = model_reliability_probability(model_for_map, grid, tau,
                                         sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD).double()
    order = torch.argsort(pmap, descending=True)
    top10 = float(true_mask[order[:10]].double().mean())
    top50 = float(true_mask[order[:50]].double().mean())
    pos, neg = pmap[true_mask], pmap[~true_mask]
    auc = (float((pos.unsqueeze(1) > neg.unsqueeze(0)).double().mean())
           if pos.numel() and neg.numel() else None)
    return {
        "family": family, "key": key, "kappa_used": kappa,
        "nonempty": bool(cert.mask.any()),
        "empirical": empirical,
        "volume": cert.volume,
        "selection": cert.selection_containment,
        "crossfit": cert.crossfit_containment,
        "true_prevalence": float(true_mask.double().mean()),
        # how much of the issued set is truly reliable, when it is not fully contained
        "hit_fraction": (float(true_mask[cert.mask].double().mean())
                         if bool(cert.mask.any()) else None),
        "map_auc": auc, "top10_precision": top10, "top50_precision": top50,
    }


def summarise(rows, label):
    ne = [r for r in rows if r["nonempty"]]
    emp = [r["empirical"] for r in ne]
    out = {
        "label": label, "n": len(rows),
        "answer_rate": len(ne) / len(rows) if rows else 0.0,
        "containment": (sum(bool(e) for e in emp) / len(emp)) if emp else None,
        "med_volume": statistics.median([r["volume"] for r in ne]) if ne else None,
        "med_selection": statistics.median([r["selection"] for r in ne]) if ne else None,
        "med_crossfit": statistics.median([r["crossfit"] for r in ne]) if ne else None,
        "med_hit_fraction": statistics.median([r["hit_fraction"] for r in ne]) if ne else None,
        "med_true_prevalence": statistics.median([r["true_prevalence"] for r in rows]),
        "containment_lb95": (clopper_pearson_lower(sum(bool(e) for e in emp), len(emp))
                             if emp else None),
        "med_kappa": statistics.median([r["kappa_used"] for r in rows]),
        "med_map_auc": statistics.median([r["map_auc"] for r in rows]),
        "med_top10_precision": statistics.median([r["top10_precision"] for r in rows]),
        "med_top50_precision": statistics.median([r["top50_precision"] for r in rows]),
    }
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--families", default="levy,rosenbrock,hill,ackley,hartmann6")
    p.add_argument("--keys", type=int, default=6)
    p.add_argument("--key-offset", type=int, default=0)
    p.add_argument("--cert-grid", type=int, default=2048)
    p.add_argument("--draws", type=int, default=4096)
    p.add_argument("--n-rho", type=int, default=64)
    p.add_argument("--alpha", type=float, default=ALPHA)
    p.add_argument("--volume-rule", default="smallest")
    p.add_argument("--budget", type=int, default=BUDGET)
    p.add_argument("--members", type=int, default=1)
    p.add_argument("--kappa", type=float, default=1.0)
    p.add_argument("--loo-scale", type=float, default=0.0)
    p.add_argument("--design", default="sobol")
    p.add_argument("--rho", type=float, default=0.5)
    p.add_argument("--label", default="baseline")
    p.add_argument("--out", default="")
    a = p.parse_args()

    rows, t0 = [], time.time()
    for fam in a.families.split(","):
        for k in range(a.key_offset, a.key_offset + a.keys):
            r = one_key(fam, k, cert_grid=a.cert_grid, draws=a.draws, n_rho=a.n_rho,
                        alpha=a.alpha, volume_rule=a.volume_rule, budget=a.budget,
                        members=a.members, kappa=a.kappa,
                        loo_scale=a.loo_scale,
                        design=a.design, rho=a.rho)
            rows.append(r)
            print(f"  {fam:11s} key{k} nonempty={r['nonempty']} emp={r['empirical']} "
                  f"vol={r['volume']:.4f} hit={r['hit_fraction']}", flush=True)
    s = summarise(rows, a.label)
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(json.dumps(s, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps({"summary": s, "rows": rows}, indent=2))
