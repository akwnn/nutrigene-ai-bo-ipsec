"""PF3 — API signature checks on the *installed* BoTorch (Person B, Gate 1).

Answers the five questions in person_b_spec.md §"Gate 1 / PF3", reading every
answer off the installed objects rather than off the spec.

Run:  python scripts/preflight_pf3.py
"""

from __future__ import annotations

import os

# Two threading settings, not one: some builds fix the OpenMP pool at import.
os.environ.setdefault("OMP_NUM_THREADS", "1")

import inspect
import warnings

import torch

torch.set_num_threads(1)

import botorch
import gpytorch
from botorch.models import SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel

SEP = "=" * 78


def rule(title: str) -> None:
    print(f"\n{SEP}\n{title}\n{SEP}")


def kernel_base(kernel) -> object:
    """Defensive traversal: unwrap ScaleKernel (and nested wrappers) to the base.

    The primary config wraps the covar module in ScaleKernel; the raw factory
    returns a bare kernel. Any hardcoded `.base_kernel` path breaks on one of
    the two, so every identity/lengthscale access goes through here.
    """
    seen = 0
    while hasattr(kernel, "base_kernel") and seen < 10:
        kernel = kernel.base_kernel
        seen += 1
    return kernel


def kernel_lengthscale(kernel) -> torch.Tensor:
    return kernel_base(kernel).lengthscale


# ---------------------------------------------------------------------------
rule("VERSIONS")
print(f"botorch  {botorch.__version__}")
print(f"gpytorch {gpytorch.__version__}")
print(f"torch    {torch.__version__}")


# ---------------------------------------------------------------------------
rule("Q1 — get_covar_module_with_dim_scaled_prior: use_rbf_kernel + return type")

from botorch.models.utils.gpytorch_modules import (  # noqa: E402
    get_covar_module_with_dim_scaled_prior,
    get_matern_kernel_with_gamma_prior,
)

sig = inspect.signature(get_covar_module_with_dim_scaled_prior)
print(f"signature: get_covar_module_with_dim_scaled_prior{sig}")
print(f"accepts use_rbf_kernel : {'use_rbf_kernel' in sig.parameters}")
if "use_rbf_kernel" in sig.parameters:
    print(f"use_rbf_kernel default : {sig.parameters['use_rbf_kernel'].default}")

D = 6
k_default = get_covar_module_with_dim_scaled_prior(ard_num_dims=D)
k_matern = get_covar_module_with_dim_scaled_prior(ard_num_dims=D, use_rbf_kernel=False)

print(f"\nreturn type (default)          : {type(k_default).__name__}")
print(f"return type (use_rbf=False)    : {type(k_matern).__name__}")
print(f"wrapped in ScaleKernel?        : {isinstance(k_default, ScaleKernel)}")
print(f"default is RBF?                : {isinstance(k_default, RBFKernel)}")
print(f"override gives Matern?         : {isinstance(k_matern, MaternKernel)}")
if isinstance(k_matern, MaternKernel):
    print(f"Matern nu                      : {k_matern.nu}")
print(f".base_kernel present on bare?  : {hasattr(k_matern, 'base_kernel')}")
print(f"lengthscale shape (bare)       : {tuple(k_matern.lengthscale.shape)}")
print(
    "legacy get_matern_kernel_with_gamma_prior returns: "
    f"{type(get_matern_kernel_with_gamma_prior(ard_num_dims=D)).__name__}"
)

# The traversal helper must work on BOTH configurations.
wrapped = ScaleKernel(
    get_covar_module_with_dim_scaled_prior(ard_num_dims=D, use_rbf_kernel=False)
)
print("\ntraversal helper check:")
print(f"  bare    -> {type(kernel_base(k_matern)).__name__}, "
      f"lengthscale {tuple(kernel_lengthscale(k_matern).shape)}")
print(f"  wrapped -> {type(kernel_base(wrapped)).__name__}, "
      f"lengthscale {tuple(kernel_lengthscale(wrapped).shape)}")


# ---------------------------------------------------------------------------
rule("Q4 — lengthscale constraint lower bound (read off the object, not hardcoded)")

for name, k in (("bare Matern", k_matern), ("ScaleKernel(Matern)", wrapped)):
    base = kernel_base(k)
    con = base.raw_lengthscale_constraint
    print(f"{name}:")
    print(f"  constraint            : {type(con).__name__}")
    print(f"  lower_bound           : {con.lower_bound}")
    print(f"  upper_bound           : {con.upper_bound}")
    prior = getattr(base, "lengthscale_prior", None)
    if prior is not None:
        print(f"  lengthscale_prior     : {type(prior).__name__} "
              f"loc={getattr(prior, 'loc', None)} scale={getattr(prior, 'scale', None)}")
print(f"\nScaleKernel outputscale constraint lower_bound: "
      f"{wrapped.raw_outputscale_constraint.lower_bound}")


# ---------------------------------------------------------------------------
rule("Q2 — Normalize without bounds=: does it learn from training-data min/max?")

# Deliberately a sub-box, exactly as E4's training data is.
sub = torch.rand(24, D, dtype=torch.double) * 0.32  # roughly [0, 0.32]^6
x_extrap = torch.full((1, D), 0.85, dtype=torch.double)

n_nobounds = Normalize(d=D)
n_nobounds.train()
_ = n_nobounds(sub)  # fitting happens in train mode
n_nobounds.eval()

n_bounded = Normalize(
    d=D, bounds=torch.stack([torch.zeros(D, dtype=torch.double),
                             torch.ones(D, dtype=torch.double)])
)
n_bounded.eval()

print(f"Normalize signature: Normalize{inspect.signature(Normalize.__init__)}")
print(f"\nsub-box data range per-dim (min/max): "
      f"{sub.min(0).values[:3].tolist()} ... / {sub.max(0).values[:3].tolist()} ...")
print(f"learned coefficient (no bounds=)   : {n_nobounds.coefficient.flatten()[:3].tolist()}")
print(f"learned offset      (no bounds=)   : {n_nobounds.offset.flatten()[:3].tolist()}")
print(f"\nextrapolation point x=0.85 maps to:")
print(f"  WITHOUT explicit bounds : {n_nobounds(x_extrap).flatten()[:3].tolist()}  "
      f"(max {n_nobounds(x_extrap).max().item():.3f})")
print(f"  WITH explicit bounds    : {n_bounded(x_extrap).flatten()[:3].tolist()}  "
      f"(max {n_bounded(x_extrap).max().item():.3f})")
print("\nVERDICT: learns from train min/max ->",
      bool(torch.allclose(n_nobounds.offset.flatten(), sub.min(0).values)))


# ---------------------------------------------------------------------------
rule("Q3 — discrete-candidate acquisition: name and signature")

import botorch.optim.optimize as _opt  # noqa: E402

discrete_fns = sorted(
    n for n in dir(_opt)
    if n.startswith("optimize_acqf") and "discrete" in n.lower()
)
print(f"discrete-capable entry points in botorch.optim.optimize: {discrete_fns}")
for name in discrete_fns:
    fn = getattr(_opt, name)
    print(f"\n{name}{inspect.signature(fn)}")
    doc = (fn.__doc__ or "").strip().splitlines()
    print("  doc: " + (doc[0] if doc else "(none)"))

try:
    from botorch.utils.sampling import sparse_to_dense_constraints  # noqa: F401
except Exception:
    pass


# ---------------------------------------------------------------------------
rule("Q5 — observation_noise=True under a FIXED-NOISE likelihood at an UNEVALUATED input")
print("(person_b_spec.md: 'Number 5 is the one that matters most.')\n")

torch.manual_seed(0)
train_X = torch.rand(20, D, dtype=torch.double) * 0.5
train_Y = torch.sin(train_X.sum(-1, keepdim=True)) + 1.0
# Deliberately heteroskedastic and easy to recognise in the output.
train_Yvar = torch.linspace(0.001, 0.05, 20, dtype=torch.double).unsqueeze(-1)

model = SingleTaskGP(
    train_X,
    train_Y,
    train_Yvar,
    covar_module=ScaleKernel(
        get_covar_module_with_dim_scaled_prior(ard_num_dims=D, use_rbf_kernel=False)
    ),
    input_transform=Normalize(
        d=D,
        bounds=torch.stack([torch.zeros(D, dtype=torch.double),
                            torch.ones(D, dtype=torch.double)]),
    ),
    outcome_transform=Standardize(m=1),
)
model.eval()

print(f"likelihood class      : {type(model.likelihood).__name__}")
nc = model.likelihood.noise_covar
print(f"noise_covar class     : {type(nc).__name__}")
print(f"has second_noise_covar: {hasattr(model.likelihood, 'second_noise_covar')}")
if hasattr(model.likelihood, "second_noise_covar"):
    print(f"  second_noise_covar  : {model.likelihood.second_noise_covar}")
print(f"train_Yvar min/mean/max (raw units): "
      f"{train_Yvar.min():.5f} / {train_Yvar.mean():.5f} / {train_Yvar.max():.5f}")

X_new = torch.rand(5, D, dtype=torch.double) * 0.5 + 0.4  # NOT in train_X

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    post_f = model.posterior(X_new, observation_noise=False)
    var_latent = post_f.variance.flatten()
    err_latent = None
    try:
        post_y = model.posterior(X_new, observation_noise=True)
        var_obs = post_y.variance.flatten()
    except Exception as e:  # noqa: BLE001
        var_obs, err_latent = None, e

print(f"\nwarnings raised       : {[str(w.message)[:110] for w in caught] or 'NONE'}")
if err_latent is not None:
    print(f"observation_noise=True RAISED: {type(err_latent).__name__}: {err_latent}")
else:
    delta = (var_obs - var_latent)
    print(f"\nlatent variance       : {[f'{v:.6f}' for v in var_latent.tolist()]}")
    print(f"observed variance     : {[f'{v:.6f}' for v in var_obs.tolist()]}")
    print(f"ADDED NOISE (delta)   : {[f'{v:.6f}' for v in delta.tolist()]}")
    print(f"\ndelta constant across the 5 new points? "
          f"{bool(torch.allclose(delta, delta[0], atol=1e-9))}")
    print("delta vs candidate explanations for what it substituted:")
    for label, val in (
        ("train_Yvar.mean()", train_Yvar.mean().item()),
        ("train_Yvar[0]", train_Yvar[0].item()),
        ("train_Yvar[-1]", train_Yvar[-1].item()),
        ("train_Yvar.min()", train_Yvar.min().item()),
        ("train_Yvar.max()", train_Yvar.max().item()),
    ):
        print(f"  {label:<20} = {val:.6f}   match: "
              f"{bool(abs(delta[0].item() - val) < 1e-6)}")

# Same question, the way E3 will actually hit it.
rule("Q5b — batch_cross_validation(observation_noise=True) on the same fixed-noise model")
from botorch.cross_validation import batch_cross_validation, gen_loo_cv_folds  # noqa: E402
from botorch.models import SingleTaskGP as _STGP  # noqa: E402
from gpytorch.mlls import ExactMarginalLogLikelihood  # noqa: E402

print(f"batch_cross_validation{inspect.signature(batch_cross_validation)}")
print(f"gen_loo_cv_folds{inspect.signature(gen_loo_cv_folds)}")

folds = gen_loo_cv_folds(train_X=train_X, train_Y=train_Y, train_Yvar=train_Yvar)
for obs_noise in (False, True):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            cv = batch_cross_validation(
                model_cls=_STGP,
                mll_cls=ExactMarginalLogLikelihood,
                cv_folds=folds,
                observation_noise=obs_noise,
            )
            v = cv.posterior.variance.flatten()
            print(f"\nobservation_noise={obs_noise}: mean fold variance {v.mean():.6f}")
        except Exception as e:  # noqa: BLE001
            print(f"\nobservation_noise={obs_noise}: RAISED {type(e).__name__}: {e}")
    msgs = {str(w.message)[:110] for w in caught}
    print(f"  warnings: {sorted(msgs) or 'NONE'}")

print(f"\n{SEP}\nPF3 complete.\n{SEP}")
