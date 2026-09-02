"""Stepwise uncertainty reduction on CERTIFIED VOLUME -- the objective itself.

**Why this exists.** `boec.lse`'s docstring calls Bryan's straddle *"the practical stand-in
for Chevalier et al.'s (Technometrics 2014) closed-form parallel SUR"*. The stand-in is all
this project has ever run. Straddle, predictive straddle and certificate-contour straddle
are all **proxies for a quantity none of them computes**.

The certificate maximises the volume of `S` with `P(S subset {f > tau}) >= alpha`. That
joint probability decays **multiplicatively** when uncertainty across the region is
independent, and barely moves when it is correlated. So the most valuable well is neither
the most uncertain point nor the one nearest the contour: it is the one whose measurement
removes the most **independent ways the region can fail**. No pointwise criterion can see
that, because it is a property of the covariance, not of any single location.

**Why it is computable in closed form.** A GP's posterior variance update does not depend
on the observed value (Rasmussen & Williams 2006, eq. 2.26):

    Sigma_new = Sigma - Sigma[:, i] Sigma[i, :] / (Sigma[i, i] + noise)

so the covariance *after* measuring point `i` is known *before* measuring it. This module
scores candidates by the certified volume implied by that updated covariance, holding the
mean fixed.

**The approximation, stated plainly.** Holding the mean fixed is a real approximation: a
measurement moves the posterior mean too, and that can raise or lower certified volume.
Integrating over the unknown observation is the full SUR criterion. This variance-only form
is deterministic, needs no nested simulation, and captures the effect the mean cannot --
the collapse of independent failure directions. It is a **lower-variance, biased** estimate
of the true gain, and any result from it must be reported as such.

Prior art: Chevalier, Bect, Ginsbourger, Vazquez, Picheny & Richet, *Technometrics* 56(4),
2014; Azzimonti, Ginsbourger, Chevalier, Bect & Richet, *SIAM/ASA JUQ*, 2021.
"""
from __future__ import annotations

import torch

from boec.vorobev import conservative_estimate

_JITTER = 1e-9


def certified_volume(mean: torch.Tensor, cov: torch.Tensor, tau: float, alpha: float,
                     n_draws: int = 2000, seed: int = 0) -> float:
    """Fraction of the grid certifiable above ``tau`` at joint level ``alpha``.

    Draws are JOINT (Cholesky of the full covariance). The certificate is a simultaneous
    claim; independent pointwise draws would overstate it badly.
    """
    q = cov.shape[0]
    c = cov + _JITTER * torch.eye(q, dtype=torch.double)
    L = torch.linalg.cholesky(c)
    z = torch.randn(q, int(n_draws), generator=torch.Generator().manual_seed(int(seed)),
                    dtype=torch.double)
    draws = (mean.reshape(-1, 1) + L @ z).T
    return float(conservative_estimate(draws, float(tau), float(alpha)).double().mean())


def _update(cov: torch.Tensor, i: int, noise: float) -> torch.Tensor:
    """Posterior covariance after measuring grid point ``i``. Exact, y-free."""
    col = cov[:, i]
    denom = float(cov[i, i]) + float(noise)
    if denom <= 0:
        return cov
    return cov - torch.outer(col, col) / denom


def sur_gain(mean: torch.Tensor, cov: torch.Tensor, tau: float, alpha: float,
             noise: float, idx, n_draws: int = 2000, seed: int = 0) -> torch.Tensor:
    """Increase in certified volume from measuring each candidate in ``idx``.

    Returns a tensor aligned with ``idx``. Non-negative by construction: the update can
    only shrink variance, and shrinking variance can only grow the certified set.

    The SAME seed is used for the base volume and every candidate, so the comparison is
    on common random numbers. With independent draws per candidate the Monte-Carlo noise
    would swamp the gains, which are small relative to the volume itself.
    """
    base = certified_volume(mean, cov, tau, alpha, n_draws, seed)
    out = torch.zeros(len(idx), dtype=torch.double)
    for j, i in enumerate(idx):
        v = certified_volume(mean, _update(cov, int(i), noise), tau, alpha, n_draws, seed)
        out[j] = v - base
    return out


def batch_sur(mean: torch.Tensor, cov: torch.Tensor, tau: float, alpha: float,
              noise: float, q: int, n_draws: int = 2000, seed: int = 0,
              n_cand: int | None = None) -> list[int]:
    """Greedy batch of ``q`` grid indices maximising certified-volume gain.

    Greedy with a REAL covariance update between picks, not a re-score of a stale
    surface. That is what makes exclusion radii unnecessary here: once point `i` is
    selected, its neighbours' variance has genuinely collapsed in `cov`, so they stop
    scoring well on their own. `boec.lse` needs a hand-tuned exclusion ball precisely
    because the straddle surface does not update.

    ``n_cand`` subsamples the candidate set; cost is O(n_cand * q) volume evaluations.
    """
    n = cov.shape[0]
    cur = cov.clone()
    pool = list(range(n))
    if n_cand is not None and n_cand < n:
        g = torch.Generator().manual_seed(int(seed))
        pool = torch.randperm(n, generator=g)[:int(n_cand)].tolist()
    chosen: list[int] = []
    for step in range(int(q)):
        cands = [i for i in pool if i not in chosen]
        if not cands:
            break
        gains = sur_gain(mean, cur, tau, alpha, noise, cands, n_draws, seed + step)
        best = cands[int(torch.argmax(gains))]
        chosen.append(best)
        cur = _update(cur, best, noise)
    return chosen
