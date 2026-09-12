"""Marginalise the GP's constant mean, so the posterior cannot collapse to zero width.

**The defect this fixes.** `boec.surrogate.build_gp` builds a `SingleTaskGP` whose
`ConstantMean` is a point estimate fitted by MLE. That estimate's uncertainty is never
propagated into the posterior. On noise-dominated data the marginal likelihood is
maximised by driving the outputscale toward zero -- the data really do look constant --
and because ALL posterior variance in that model comes from the kernel, the posterior
width goes to zero with it.

Measured on this project's own iPSC-EC coating data (`data/lab/derived/`, 12 tubes,
signal variance 49.5, measured noise variance 147.3, SNR 0.34), the posterior collapses
to **37.16 +/- 0.01** on observations spanning 22.6 to 47.3 percent CD31+. The honest
width is the standard error of a constant, `noise_sd / sqrt(n)` = 3.5. The model
understates it **350-fold**, and no amount of posterior inflation repairs it: scaling
0.01 by c=3 gives 0.03.

**The fix.** Treat the constant mean as an unknown nuisance parameter with a flat prior
and integrate it out -- ordinary kriging rather than simple kriging (Matheron 1963; see
Rasmussen & Williams 2006, sec. 2.7, "GPs with a fixed mean function"). Writing
``K = k(X,X) + noise`` and ``k_*(x) = k(X, x)``:

    u(x)          = 1 - 1' K^-1 k_*(x)
    s             = 1' K^-1 1
    cov_extra(x,y) = u(x) u(y) / s

`cov_extra` is a rank-one PSD term, so this can only ADD uncertainty -- it is
conservative by construction, in the same sense the inflation correction is. In the
noise-dominated limit ``k -> 0``, giving ``u -> 1`` and ``s -> n / sigma^2``, so the
correction tends to ``sigma^2 / n``: exactly the standard error of the mean.

**Why this is not the inflation constant `c` again.** Inflation is a scalar fitted to
truth containment and is a *variance* correction that leaves the mean untouched
(`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10.2). This has no free parameter, is exact given
the kernel, and repairs a specific structural omission. The two are independent and
compose.
"""
from __future__ import annotations

import torch

#: Jitter for the training-covariance solve. Matches the scale used elsewhere.
_JITTER = 1e-8


def _train_covariance(model) -> torch.Tensor:
    """K = k(X, X) + observation noise, in the model's internal (standardized) space."""
    Xtr = model.train_inputs[0]
    K = model.covar_module(Xtr).to_dense().double()
    noise = model.likelihood.noise.detach().reshape(-1).double()
    K = K + torch.diag(noise)
    return K + _JITTER * torch.eye(K.shape[0], dtype=torch.double)


def mean_marginalised_covariance(model, X_test: torch.Tensor) -> torch.Tensor:
    """Posterior covariance at ``X_test`` with the constant mean integrated out.

    Args:
        model: a fitted ``SingleTaskGP`` from :func:`boec.surrogate.build_gp`.
        X_test: ``(q, d)`` test points in ORIGINAL input units.

    Returns:
        ``(q, q)`` covariance in ORIGINAL output units -- the model's own posterior
        covariance plus the rank-one term contributed by not knowing the mean.

    The correction is computed in the model's standardized space and rescaled by the
    outcome transform, because that is the space the kernel and the noise live in.
    Doing it in raw units would apply the standardizer's scale twice.
    """
    X_test = torch.as_tensor(X_test).double()
    with torch.no_grad():
        post = model.posterior(X_test, observation_noise=False)
        if hasattr(post, "mvn"):
            cov = post.mvn.covariance_matrix.double()
        elif hasattr(post, "covariance_matrix"):
            cov = post.covariance_matrix.double()
        else:
            raise TypeError(
                "posterior must expose mvn.covariance_matrix or covariance_matrix "
                "for mean marginalisation"
            )

        Xtr = model.train_inputs[0]
        # transform_inputs is idempotent on already-transformed training inputs, so the
        # test points must be pushed through the SAME transform to be comparable.
        Xte = model.transform_inputs(X_test) if hasattr(model, "transform_inputs") \
            else X_test
        K = _train_covariance(model)
        k_star = model.covar_module(Xtr, Xte).to_dense().double()     # (n, q)

        ones = torch.ones(K.shape[0], 1, dtype=torch.double)
        Kinv_one = torch.linalg.solve(K, ones)                        # (n, 1)
        s = float((ones.T @ Kinv_one).squeeze())
        if s <= 0:
            return cov                                   # degenerate; add nothing
        u = 1.0 - (k_star.T @ Kinv_one).reshape(-1, 1)                # (q, 1)
        extra = (u @ u.T) / s                                         # rank one, PSD

        # Back to original output units. Standardize stores per-output stdvs.
        scale = 1.0
        ot = getattr(model, "outcome_transform", None)
        if ot is not None and hasattr(ot, "stdvs"):
            scale = float(ot.stdvs.reshape(-1)[0]) ** 2
        return cov + scale * extra
