"""PF4 — wall-clock for one 48-evaluation run, at both noise levels (Person B, Gate 1).

Also verifies the clean resolution to PF3-Q5: supplying prediction-point noise
explicitly as a tensor, instead of letting BoTorch substitute train_Yvar.mean().

STAND-IN NOTE: the biphasic oracle is Person A's module and does not exist yet.
Timing here uses Hartmann6 (d=6) and a synthetic d=8 analogue with the exact
model config, budget convention, and Yvar policy from the spec. Oracle
evaluation is arithmetic and contributes ~nothing; the cost is GP fitting plus
multi-start L-BFGS inside optimize_acqf. Re-run against the real oracle once
A ships it.

Run:  python scripts/preflight_pf4.py
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import time

import torch

torch.set_num_threads(1)

from botorch.acquisition.logei import qLogExpectedImprovement
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from botorch.models.utils.gpytorch_modules import get_covar_module_with_dim_scaled_prior
from botorch.optim import optimize_acqf
from botorch.test_functions import Hartmann
from botorch.utils.sampling import draw_sobol_samples
from gpytorch.kernels import ScaleKernel
from gpytorch.mlls import ExactMarginalLogLikelihood

DTYPE = torch.double
SIGMA_ADD = 0.01


def make_objective(d: int):
    """Positive, order-1 stand-in with an interior optimum. Returns f(X) -> (n,1)."""
    if d == 6:
        h = Hartmann(dim=6, negate=True)  # max ~3.32

        def f(X: torch.Tensor) -> torch.Tensor:
            return (h(X).unsqueeze(-1) / 3.32).clamp_min(1e-6)

        return f

    # d=8 analogue: separable biphasic-ish bumps, peak ~1.0, interior optimum.
    centers = torch.linspace(0.3, 0.55, d, dtype=DTYPE)

    def f(X: torch.Tensor) -> torch.Tensor:
        return (torch.exp(-((X - centers) ** 2) / 0.08).mean(-1, keepdim=True)).clamp_min(1e-6)

    return f


def build_gp(train_X, train_Y, train_Yvar, bounds):
    d = train_X.shape[-1]
    covar = ScaleKernel(
        # use_rbf_kernel defaults to True -> RBF. Override is required for Matern 5/2.
        get_covar_module_with_dim_scaled_prior(ard_num_dims=d, use_rbf_kernel=False)
    )
    model = SingleTaskGP(
        train_X,
        train_Y,
        train_Yvar,
        covar_module=covar,
        # Explicit bounds always: learned bounds break E4's sub-box silently.
        input_transform=Normalize(d=d, bounds=bounds),
        outcome_transform=Standardize(m=1),
    )
    fit_gpytorch_mll(ExactMarginalLogLikelihood(model.likelihood, model))
    return model


def observe(f, X, sigma_rel, gen):
    """y = f(x)(1+eps) + eta; Yvar is the PLUG-IN estimate from the observed value."""
    y_true = f(X)
    eps = torch.randn(y_true.shape, dtype=DTYPE, generator=gen) * sigma_rel
    eta = torch.randn(y_true.shape, dtype=DTYPE, generator=gen) * SIGMA_ADD
    y_obs = y_true * (1 + eps) + eta
    y_var = (y_obs**2 * sigma_rel**2 + SIGMA_ADD**2).clamp_min(1e-8)
    return y_obs, y_var


def run_campaign(d: int, sigma_rel: float, seed: int = 0, verbose: bool = False):
    """Budget convention from spec §E2: d=6 -> 14 + 8x4 + 2; d=8 -> 18 + 7x4 + 2."""
    gen = torch.Generator().manual_seed(seed)
    torch.manual_seed(seed)
    f = make_objective(d)
    bounds = torch.stack([torch.zeros(d, dtype=DTYPE), torch.ones(d, dtype=DTYPE)])

    n_init = 2 * d + 2
    batches = [4] * ((48 - n_init - 2) // 4) + [2]
    assert n_init + sum(batches) == 48, (n_init, batches)

    X = draw_sobol_samples(bounds=bounds, n=n_init, q=1, seed=seed).squeeze(1)
    Y, Yvar = observe(f, X, sigma_rel, gen)

    fit_s, acq_s = 0.0, 0.0
    for q in batches:
        t0 = time.perf_counter()
        model = build_gp(X, Y, Yvar, bounds)
        fit_s += time.perf_counter() - t0

        t0 = time.perf_counter()
        acqf = qLogExpectedImprovement(model=model, best_f=Y.max())
        # Joint q-acquisition, never top-q of a single-point surface.
        cand, _ = optimize_acqf(
            acq_function=acqf, bounds=bounds, q=q, num_restarts=10, raw_samples=512
        )
        acq_s += time.perf_counter() - t0

        Yn, Vn = observe(f, cand, sigma_rel, gen)
        X, Y, Yvar = torch.cat([X, cand]), torch.cat([Y, Yn]), torch.cat([Yvar, Vn])

    assert X.shape[0] == 48
    return fit_s, acq_s, len(batches)


def verify_explicit_noise():
    """PF3-Q5 resolution: pass prediction-point noise as a tensor."""
    d = 6
    torch.manual_seed(0)
    tX = torch.rand(20, d, dtype=DTYPE) * 0.5
    tY = torch.sin(tX.sum(-1, keepdim=True)) + 1.0
    tV = torch.linspace(0.001, 0.05, 20, dtype=DTYPE).unsqueeze(-1)
    bounds = torch.stack([torch.zeros(d, dtype=DTYPE), torch.ones(d, dtype=DTYPE)])
    m = SingleTaskGP(
        tX, tY, tV,
        covar_module=ScaleKernel(
            get_covar_module_with_dim_scaled_prior(ard_num_dims=d, use_rbf_kernel=False)
        ),
        input_transform=Normalize(d=d, bounds=bounds),
        outcome_transform=Standardize(m=1),
    )
    m.eval()
    Xn = torch.rand(5, d, dtype=DTYPE) * 0.4 + 0.5

    v_latent = m.posterior(Xn, observation_noise=False).variance.flatten()
    v_auto = m.posterior(Xn, observation_noise=True).variance.flatten()
    # What the plug-in formula would give at these points, per-point and distinct.
    mu = m.posterior(Xn).mean
    v_plugin = (mu**2 * 0.10**2 + SIGMA_ADD**2)
    v_supplied = m.posterior(Xn, observation_noise=v_plugin).variance.flatten()

    print("\n--- PF3-Q5 resolution: explicit per-point noise ---")
    print(f"train_Yvar.mean()            : {tV.mean().item():.6f}")
    print(f"delta with observation_noise=True   (auto): "
          f"{[f'{v:.6f}' for v in (v_auto - v_latent).tolist()]}")
    print(f"plug-in noise we supply     : {[f'{v:.6f}' for v in v_plugin.flatten().tolist()]}")
    print(f"delta with supplied tensor  : "
          f"{[f'{v:.6f}' for v in (v_supplied - v_latent).tolist()]}")
    ok = torch.allclose((v_supplied - v_latent), v_plugin.flatten(), atol=1e-8)
    print(f"supplied noise honoured exactly, per-point : {ok}")
    print("  -> tensor path is per-point; bool path is a single mean for every point.")
    return ok


if __name__ == "__main__":
    print("=" * 78)
    print("PF4 — wall-clock, one 48-evaluation qLogEI run (STAND-IN objective)")
    print("=" * 78)
    print(f"threads: torch={torch.get_num_threads()} OMP={os.environ.get('OMP_NUM_THREADS')}")

    rows = []
    for d in (6, 8):
        for sigma_rel in (0.10, 0.25):
            t0 = time.perf_counter()
            fit_s, acq_s, n_rounds = run_campaign(d, sigma_rel)
            total = time.perf_counter() - t0
            rows.append((d, sigma_rel, total, fit_s, acq_s, n_rounds))
            print(f"\nd={d}  sigma_rel={sigma_rel:.2f}  rounds={n_rounds}")
            print(f"  total          {total:7.2f} s")
            print(f"  GP fitting     {fit_s:7.2f} s  ({fit_s / total:5.1%})")
            print(f"  optimize_acqf  {acq_s:7.2f} s  ({acq_s / total:5.1%})")
            print(f"  per round      {total / n_rounds:7.2f} s")

    print("\n" + "=" * 78)
    print("GRID PROJECTION  (E2: 10 instances x 5 seeds x d{6,8} x 2 noise levels)")
    print("=" * 78)
    per_d = {}
    for d, s, total, *_ in rows:
        per_d.setdefault(d, []).append(total)
    bo_total = sum(sum(v) for v in per_d.values()) * 10 * 5  # 10 inst x 5 seeds
    print(f"qLogEI arm only, single-threaded : {bo_total / 3600:6.2f} h")
    print(f"  at 4 workers                   : {bo_total / 3600 / 4:6.2f} h")
    print(f"  at 8 workers                   : {bo_total / 3600 / 8:6.2f} h")
    print("(random/Sobol/LHS arms fit no model -> near-instant. The sequential DoE")
    print(" arm fits one polynomial per stage -> negligible. E4 adds 10 inst x 4 kappa")
    print(" GP fits, each a single fit rather than a campaign.)")

    verify_explicit_noise()
    print("\n" + "=" * 78)
    print("PF4 complete.")
    print("=" * 78)
