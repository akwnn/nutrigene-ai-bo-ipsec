"""Hyperparameter-mixture posteriors: attack the bias that inflation cannot reach.

**The limit this addresses.** `SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10.2 established,
on a fixed cohort so survivorship is removed, that posterior inflation cures
under-dispersion and nothing else. It scales the posterior SD and leaves the mean exactly
where it was, while the Vorob'ev quantile shrinks the certified region toward its
HIGHEST-excursion-probability points. A point the model is *confidently wrong* about is
therefore retained at every value of `c`, by construction. Measured consequence: `levy`
and `rosenbrock` saturate at truth containment 0.75 and 0.73 and no inflation moves them,
while `ackley` and `hartmann6` climb monotonically to 0.93 and 0.88.

**Why a mixture can move what a scalar cannot.** `build_gp` fits the lengthscale and
outputscale by maximum likelihood and then treats them as known. Any error in them is a
*structured* error in the posterior mean -- an over-long lengthscale smooths a real
feature away, and the resulting mean is confidently wrong in a spatially organised
pattern. Averaging over several marginal-likelihood-weighted fits changes the **shape**
of the posterior, not merely its width, and is the cheapest honest approximation to
integrating the hyperparameters out.

This is the dependency-free stand-in for full NUTS marginalisation
(`SaasFullyBayesianSingleTaskGP`), which needs JAX and NumPyro. It is an approximation and
is labelled as one: restarts explore the likelihood surface, they do not sample it.

**Registered expectation, before any result.** If levy/rosenbrock saturation is driven by
hyperparameter misspecification, mixing should raise their ceiling. If it is driven by
something else -- too few wells near the contour, a mis-specified noise model -- mixing
will not help, and that is an informative negative.
"""
from __future__ import annotations

import torch

#: Restarts below this log-likelihood share of the best are dropped as failed fits.
_WEIGHT_FLOOR = 1e-6


def hyperparameter_ensemble(train_X, train_Y, train_Yvar, bounds, n_models: int = 5,
                            seed: int = 0):
    """Fit ``n_models`` GPs from different initialisations, weighted by evidence.

    Args:
        train_X, train_Y, train_Yvar, bounds: as :func:`boec.surrogate.build_gp`.
        n_models: number of restarts. Cost is linear in this.
        seed: seeds torch's RNG before each fit, so the ensemble is reproducible.

    Returns:
        ``(models, weights)`` -- weights are the softmax of each fit's marginal
        log-likelihood, normalised, which is the Bayesian evidence weight under a flat
        prior over the restarts. A restart that failed to move off its initialisation
        gets a low weight rather than an equal vote, which is the whole point of
        weighting by evidence instead of averaging.
    """
    from gpytorch.mlls import ExactMarginalLogLikelihood

    from boec.surrogate import build_gp

    from botorch.fit import fit_gpytorch_mll

    models, mlls = [], []
    for i in range(int(n_models)):
        # build_gp's fit is DETERMINISTIC given the data -- seeding torch does not move
        # it, and an unperturbed "ensemble" is five copies of one model. A test caught
        # exactly that. The initialisation must be perturbed explicitly for the restarts
        # to explore different basins of the likelihood surface.
        m = build_gp(train_X, train_Y, train_Yvar, bounds, fit=False)
        if i > 0:
            g = torch.Generator().manual_seed(int(seed) * 1000 + i)
            with torch.no_grad():
                for name, param in m.named_parameters():
                    if "raw_lengthscale" in name or "raw_outputscale" in name:
                        param.add_(0.75 * torch.randn(param.shape, generator=g,
                                                      dtype=param.dtype))
        mll = ExactMarginalLogLikelihood(m.likelihood, m)
        try:
            fit_gpytorch_mll(mll)
        except Exception:
            pass                       # a diverged restart keeps its perturbed state and
                                       # will simply earn a low evidence weight
        with torch.no_grad():
            val = float(mll(m(*m.train_inputs), m.train_targets))
        models.append(m)
        mlls.append(val)

    t = torch.tensor(mlls, dtype=torch.double)
    w = torch.softmax(t - t.max(), dim=0)
    w = torch.where(w < _WEIGHT_FLOOR, torch.zeros_like(w), w)
    w = w / w.sum()
    return models, w


def mixture_draws(models, weights, X_test, n_draws: int = 4000, seed: int = 0,
                  inflation: float = 1.0) -> torch.Tensor:
    """Joint posterior draws from the evidence-weighted mixture.

    Args:
        models, weights: from :func:`hyperparameter_ensemble`.
        X_test: ``(q, d)`` points to draw at.
        n_draws: total draws returned.
        seed: reproducibility.
        inflation: optional posterior-SD scaling, applied WITHIN each component so the
            two corrections compose rather than compete.

    Returns:
        ``(n_draws, q)``, the same orientation `boec.vorobev` expects.

    Each component is allocated a share of the draws proportional to its weight, so the
    returned sample is from the mixture rather than from any single fit. Drawing jointly
    (Cholesky of the full covariance) rather than pointwise is required: the certificate
    is a SIMULTANEOUS claim, and independent pointwise draws would understate the joint
    probability of a whole region.
    """
    X_test = torch.as_tensor(X_test).double()
    q = X_test.shape[0]
    w = torch.as_tensor(weights, dtype=torch.double)
    counts = torch.floor(w * n_draws).to(torch.long)
    counts[int(torch.argmax(w))] += n_draws - int(counts.sum())   # exact total

    out = torch.empty(n_draws, q, dtype=torch.double)
    at = 0
    for i, (m, k) in enumerate(zip(models, counts.tolist())):
        if k <= 0:
            continue
        with torch.no_grad():
            post = m.posterior(X_test)
            mean = post.mean.reshape(-1, 1).double()
            cov = post.mvn.covariance_matrix.double()
            cov = cov + 1e-8 * torch.eye(q, dtype=torch.double)
            L = torch.linalg.cholesky(cov)
            g = torch.Generator().manual_seed(int(seed) * 977 + i)
            z = torch.randn(q, k, generator=g, dtype=torch.double)
            out[at:at + k] = (mean + float(inflation) * L @ z).T
        at += k
    return out
