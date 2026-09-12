"""Future-response reliability maps and empirically testable set certificates.

The target is predictive: a recipe is reliable when a *future observation* clears
``tau`` with probability at least ``gamma``.  Posterior latent uncertainty is used for
the probability map, while certificate draws sample the latent field jointly and then
apply the learned observation-noise margin to each sampled field.

The returned cross-fit containment is a model diagnostic.  Confirmatory containment is
the campaign-level subset check against sealed oracle truth implemented by
:func:`empirical_set_containment`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral, Real

import torch
from scipy.stats import beta
from torch import Tensor

from boec.surrogate import outcome_scale
from boec.vorobev import set_containment_probability, vorobev_quantile

__all__ = [
    "ConservativeSetResult",
    "clopper_pearson_lower",
    "conservative_set_split",
    "empirical_set_containment",
    "model_reliability_probability",
    "reliable_set_draws",
    "true_reliability_probability",
]


@dataclass(frozen=True)
class ConservativeSetResult:
    """A set selected on one draw half and evaluated on the other."""

    mask: Tensor
    crossfit_containment: float | None
    selection_containment: float | None
    volume: float
    selection_draws: int
    evaluation_draws: int


def _finite_scalar(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _open_probability(value: Real, name: str) -> float:
    result = _finite_scalar(value, name)
    if not 0.0 < result < 1.0:
        raise ValueError(f"{name} must lie strictly between 0 and 1, got {result}")
    return result


def _standard_normal_cdf(value: Tensor) -> Tensor:
    normal = torch.distributions.Normal(
        torch.zeros((), dtype=value.dtype, device=value.device),
        torch.ones((), dtype=value.dtype, device=value.device),
    )
    return normal.cdf(value)


def _validate_X(X: Tensor) -> None:
    if not isinstance(X, Tensor) or X.ndim != 2:
        shape = tuple(X.shape) if isinstance(X, Tensor) else type(X).__name__
        raise ValueError(f"X must have shape (n_grid, d), got {shape}")
    if X.shape[0] < 1 or X.shape[1] < 1:
        raise ValueError("X must contain at least one grid point and one factor")
    if not bool(torch.isfinite(X).all()):
        raise ValueError("X must contain only finite coordinates")


def _learned_noise_variance(model) -> Tensor:
    try:
        standardized = model.likelihood.noise.detach().double().reshape(-1)
        scale = outcome_scale(model).detach().double().reshape(-1)
    except (AttributeError, ValueError) as exc:
        raise ValueError(
            "model must expose one learned homoskedastic likelihood noise value "
            "and one outcome scale"
        ) from exc
    if standardized.numel() != 1 or scale.numel() != 1:
        raise ValueError("model noise must be one learned homoskedastic value")
    variance = standardized[0] * scale[0].square()
    if not bool(torch.isfinite(variance)) or float(variance) <= 0.0:
        raise ValueError("learned likelihood noise must be positive and finite")
    return variance


def _latent_posterior(model, X: Tensor):
    _validate_X(X)
    model.eval()
    with torch.no_grad():
        posterior = model.posterior(X.double(), observation_noise=False)
        mean = posterior.mean
        variance = posterior.variance
    expected = (X.shape[0], 1)
    if tuple(mean.shape) != expected or tuple(variance.shape) != expected:
        raise ValueError(
            "single-outcome posterior mean and variance must have shape "
            f"{expected}, got {tuple(mean.shape)} and {tuple(variance.shape)}"
        )
    if not bool(torch.isfinite(mean).all()) or not bool(torch.isfinite(variance).all()):
        raise ValueError("posterior mean and variance must be finite")
    if bool(torch.any(variance < 0)):
        raise ValueError("posterior variance cannot be negative")
    return posterior, mean.flatten(), variance.flatten()


def true_reliability_probability(
    f: Tensor,
    tau: Real,
    sigma_rel: Real,
    sigma_add: Real,
) -> Tensor:
    """Oracle ``P(Y_new >= tau | f)`` under relative-plus-additive noise."""
    if not isinstance(f, Tensor) or f.numel() == 0:
        raise ValueError("f must be a non-empty tensor")
    if not bool(torch.isfinite(f).all()):
        raise ValueError("f must contain only finite values")
    tau_f = _finite_scalar(tau, "tau")
    sigma_rel_f = _finite_scalar(sigma_rel, "sigma_rel")
    sigma_add_f = _finite_scalar(sigma_add, "sigma_add")
    if sigma_rel_f < 0.0 or sigma_add_f < 0.0:
        raise ValueError("noise sigmas must be nonnegative")

    values = f.double()
    noise_variance = sigma_rel_f**2 * values.square() + sigma_add_f**2
    if bool(torch.any(noise_variance <= 0.0)):
        raise ValueError("noise standard deviation must be positive at every point")
    standardized = (tau_f - values) / noise_variance.sqrt()
    return 1.0 - _standard_normal_cdf(standardized)


def model_reliability_probability(
    model,
    X: Tensor,
    tau: Real,
    *,
    sigma_rel: Real | None = None,
    sigma_add: Real | None = None,
) -> Tensor:
    """Model ``P(Y_new >= tau | data)``.

    When ``sigma_rel``/``sigma_add`` are provided, the future-observation noise matches
    the sealed assay law used by oracle truth (manufacturing recovery default).
    Otherwise the joint protocol's learned homoskedastic likelihood noise is used.
    """
    tau_f = _finite_scalar(tau, "tau")
    _, mean, latent_variance = _latent_posterior(model, X)
    if sigma_rel is None and sigma_add is None:
        noise_variance = _learned_noise_variance(model).to(latent_variance).expand_as(
            latent_variance
        )
    else:
        if sigma_rel is None or sigma_add is None:
            raise ValueError("sigma_rel and sigma_add must be provided together")
        sigma_rel_f = _finite_scalar(sigma_rel, "sigma_rel")
        sigma_add_f = _finite_scalar(sigma_add, "sigma_add")
        if sigma_rel_f < 0.0 or sigma_add_f < 0.0:
            raise ValueError("noise sigmas must be nonnegative")
        noise_variance = sigma_rel_f**2 * mean.square() + sigma_add_f**2
        if bool(torch.any(noise_variance <= 0.0)):
            raise ValueError("assay noise standard deviation must be positive everywhere")
    total_sd = (latent_variance + noise_variance).sqrt()
    return 1.0 - _standard_normal_cdf((tau_f - mean) / total_sd)


def reliable_set_draws(
    model,
    X: Tensor,
    tau: Real,
    gamma: Real,
    n_draws: int,
    seed: int,
    *,
    sigma_rel: Real | None = None,
    sigma_add: Real | None = None,
    latent_inflation: Real = 1.0,
    mean_marginalisation: bool = False,
) -> Tensor:
    """Joint posterior draws of the future-response reliable set.

    Each row is one jointly sampled latent field converted to conditional
    future-observation probabilities, then thresholded at ``gamma``.  When assay
    ``sigma_rel``/``sigma_add`` are supplied, each draw uses the same relative-plus-
    additive noise law as sealed truth; otherwise learned homoskedastic likelihood
    noise is used.  ``latent_inflation`` ≥ 1 scales deviations of each joint draw
    from the posterior mean (LOO self-calibration uses this to widen overconfident
    surrogates).  ``mean_marginalisation`` integrates out the GP constant mean
    (ordinary kriging; see :mod:`boec.meanmarg`) before sampling — independent of
    inflation, and required on noise-dominated assays where simple-kriging width
    collapses.  An even count is mandatory because certification uses equal
    selection and evaluation halves.
    """
    tau_f = _finite_scalar(tau, "tau")
    gamma_f = _open_probability(gamma, "gamma")
    kappa_f = _finite_scalar(latent_inflation, "latent_inflation")
    if kappa_f < 1.0:
        raise ValueError(f"latent_inflation must be >= 1, got {kappa_f}")
    if not isinstance(mean_marginalisation, bool):
        raise ValueError(
            f"mean_marginalisation must be bool, got {mean_marginalisation!r}"
        )
    if isinstance(n_draws, bool) or not isinstance(n_draws, Integral):
        raise ValueError(f"n_draws must be an even integer, got {n_draws!r}")
    n_draws_i = int(n_draws)
    if n_draws_i < 2 or n_draws_i % 2:
        raise ValueError(f"n_draws must be even and at least 2, got {n_draws_i}")
    if isinstance(seed, bool) or not isinstance(seed, Integral):
        raise ValueError(f"seed must be a nonnegative integer, got {seed!r}")
    seed_i = int(seed)
    if not 0 <= seed_i < 2**63:
        raise ValueError(f"seed must lie in [0, 2**63), got {seed_i}")
    use_assay = not (sigma_rel is None and sigma_add is None)
    if use_assay and (sigma_rel is None or sigma_add is None):
        raise ValueError("sigma_rel and sigma_add must be provided together")
    if use_assay:
        sigma_rel_f = _finite_scalar(sigma_rel, "sigma_rel")
        sigma_add_f = _finite_scalar(sigma_add, "sigma_add")
        if sigma_rel_f < 0.0 or sigma_add_f < 0.0:
            raise ValueError("noise sigmas must be nonnegative")
        learned_noise_variance = None
    else:
        sigma_rel_f = sigma_add_f = None
        learned_noise_variance = _learned_noise_variance(model)

    posterior, posterior_mean, _ = _latent_posterior(model, X)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed_i)

    if mean_marginalisation:
        from boec.meanmarg import mean_marginalised_covariance

        mean_vec = posterior_mean.reshape(-1).double()
        n_grid = int(mean_vec.numel())
        with torch.no_grad():
            cov = mean_marginalised_covariance(model, X.detach().double())
        if tuple(cov.shape) != (n_grid, n_grid):
            raise ValueError(
                "mean-marginalised covariance must have shape "
                f"({n_grid}, {n_grid}), got {tuple(cov.shape)}"
            )
        jitter = 1e-8 * torch.eye(n_grid, dtype=torch.double)
        try:
            chol = torch.linalg.cholesky(cov + jitter)
        except RuntimeError as exc:
            raise ValueError(
                "mean-marginalised covariance is not positive definite"
            ) from exc
        z = torch.randn(
            n_draws_i,
            n_grid,
            generator=generator,
            dtype=torch.double,
            device="cpu",
        )
        latent = mean_vec.unsqueeze(0) + z @ chol.transpose(0, 1)
    else:
        try:
            base_sample_shape = torch.Size(posterior.base_sample_shape)
            sample_from_base = posterior.rsample_from_base_samples
        except (AttributeError, TypeError) as exc:
            raise ValueError(
                "posterior must support deterministic joint sampling from base samples"
            ) from exc
        if len(base_sample_shape) == 0 or math.prod(base_sample_shape) < 1:
            raise ValueError(
                f"posterior base_sample_shape must be non-empty, got {base_sample_shape}"
            )

        sample_shape = torch.Size([n_draws_i])
        base_samples = torch.randn(
            sample_shape + base_sample_shape,
            generator=generator,
            dtype=torch.double,
            device="cpu",
        ).to(dtype=posterior_mean.dtype, device=posterior_mean.device)
        with torch.no_grad():
            latent = sample_from_base(sample_shape, base_samples)
        expected = (n_draws_i, X.shape[0], 1)
        if tuple(latent.shape) != expected:
            raise ValueError(
                f"joint posterior draws must have shape {expected}, got {tuple(latent.shape)}"
            )
        if not bool(torch.isfinite(latent).all()):
            raise ValueError("joint posterior draws must be finite")
        latent = latent.squeeze(-1).double()

    if not bool(torch.isfinite(latent).all()):
        raise ValueError("joint posterior draws must be finite")
    if kappa_f != 1.0:
        mean = posterior_mean.double().reshape(1, -1)
        latent = mean + kappa_f * (latent - mean)
    if use_assay:
        noise_variance = sigma_rel_f**2 * latent.square() + sigma_add_f**2
        if bool(torch.any(noise_variance <= 0.0)):
            raise ValueError("assay noise standard deviation must be positive everywhere")
        observation_sd = noise_variance.sqrt()
    else:
        observation_sd = learned_noise_variance.to(latent).sqrt()
    probability = 1.0 - _standard_normal_cdf((tau_f - latent) / observation_sd)
    return probability >= gamma_f


def conservative_set_split(
    set_draws: Tensor,
    alpha: Real,
    n_rho: int = 64,
    *,
    volume_rule: str = "largest",
) -> ConservativeSetResult:
    """Select a conservative Vorob'ev set and cross-fit its model containment.

    ``volume_rule="smallest"`` (registered manufacturing default) issues the smallest
    non-empty quantile whose selection-half model containment is at least ``alpha``.
    ``volume_rule="largest"`` retains the historical maximal-volume rule, which was
    over-willing under misspecified plug-in models.
    """
    alpha_f = _open_probability(alpha, "alpha")
    if volume_rule not in {"smallest", "largest"}:
        raise ValueError(
            f"volume_rule must be 'smallest' or 'largest', got {volume_rule!r}"
        )
    if not isinstance(set_draws, Tensor) or set_draws.ndim != 2:
        shape = tuple(set_draws.shape) if isinstance(set_draws, Tensor) else type(set_draws).__name__
        raise ValueError(f"set draws must have shape (n_draws, n_grid), got {shape}")
    if set_draws.dtype != torch.bool:
        raise ValueError("set draws must be boolean")
    n_draws, n_grid = set_draws.shape
    if n_grid < 1:
        raise ValueError("set draws must contain at least one grid point")
    if n_draws < 2 or n_draws % 2:
        raise ValueError("set draw count must be even and at least 2")
    if isinstance(n_rho, bool) or not isinstance(n_rho, Integral) or int(n_rho) < 2:
        raise ValueError(f"n_rho must be an integer of at least 2, got {n_rho!r}")

    half = n_draws // 2
    selection = set_draws[:half]
    evaluation = set_draws[half:]
    inclusion = selection.double().mean(dim=0)
    best = torch.zeros(n_grid, dtype=torch.bool, device=set_draws.device)
    best_containment: float | None = None
    for rho in torch.linspace(
        1.0, 0.0, int(n_rho), dtype=inclusion.dtype, device=inclusion.device
    ).tolist():
        mask = vorobev_quantile(inclusion, rho)
        size = int(mask.sum())
        if size == 0:
            continue
        containment = set_containment_probability(selection, mask)
        if containment < alpha_f:
            continue
        if volume_rule == "smallest":
            # rho decreases from 1→0, so the first admissible mask is the smallest.
            best = mask.clone()
            best_containment = containment
            break
        if size <= int(best.sum()):
            continue
        best = mask.clone()
        best_containment = containment

    if int(best.sum()) == 0:
        crossfit = None
    else:
        crossfit = set_containment_probability(evaluation, best)
    return ConservativeSetResult(
        mask=best,
        crossfit_containment=crossfit,
        selection_containment=best_containment,
        volume=float(best.double().mean()),
        selection_draws=half,
        evaluation_draws=half,
    )


def empirical_set_containment(mask: Tensor, truth_mask: Tensor) -> bool | None:
    """Whether a non-empty issued set is a subset of sealed reliable-set truth."""
    if not isinstance(mask, Tensor) or not isinstance(truth_mask, Tensor):
        raise ValueError("mask and truth_mask must be boolean tensors")
    if mask.ndim != 1 or truth_mask.ndim != 1 or mask.shape != truth_mask.shape:
        raise ValueError(
            f"mask and truth_mask must have the same one-dimensional shape, got "
            f"{tuple(mask.shape)} and {tuple(truth_mask.shape)}"
        )
    if mask.dtype != torch.bool or truth_mask.dtype != torch.bool:
        raise ValueError("mask and truth_mask must be boolean")
    if int(mask.sum()) == 0:
        return None
    return bool(truth_mask[mask].all())


def clopper_pearson_lower(
    successes: int,
    total: int,
    confidence: Real = 0.95,
) -> float | None:
    """Exact one-sided binomial lower confidence bound.

    ``None`` for a zero denominator is deliberate: no issued certificates means no
    positive evidence and therefore can never satisfy a PASS inequality.
    """
    if isinstance(successes, bool) or not isinstance(successes, Integral):
        raise ValueError("successes must be an integer")
    if isinstance(total, bool) or not isinstance(total, Integral):
        raise ValueError("total must be an integer")
    successes_i, total_i = int(successes), int(total)
    if total_i < 0:
        raise ValueError("total must be nonnegative")
    if not 0 <= successes_i <= total_i:
        raise ValueError("successes must lie between zero and total")
    confidence_f = _open_probability(confidence, "confidence")
    if total_i == 0:
        return None
    if successes_i == 0:
        return 0.0
    return float(beta.ppf(1.0 - confidence_f, successes_i, total_i - successes_i + 1))
