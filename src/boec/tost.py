"""TOST at a pre-registered SESOI, plus a Wilcoxon MDE for n=25.

An interval covering 0 is not equivalence. Both one-sided tests must reject
at alpha to call equivalent (Schuirmann / Lakens). Otherwise the contrast is
different (bootstrap interval excludes 0) or inconclusive.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy import stats

from boec.diagnostics import instance_bootstrap

__all__ = ["tost_paired", "wilcoxon_mde", "per_instance"]

SESOI_DEFAULT = 0.02


def per_instance(rows: list[dict], key: str) -> np.ndarray:
    """One number per landscape, averaging seeds. Sorted by instance id."""
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(str(r["instance"]), []).append(float(r[key]))
    return np.array([float(np.mean(v)) for _, v in sorted(by.items())])


def tost_paired(
    diffs: Sequence[float] | np.ndarray,
    *,
    sesoi: float = SESOI_DEFAULT,
    alpha: float = 0.05,
    n_boot: int = 4000,
    seed: int = 0,
) -> dict:
    """Two one-sided t-tests on paired landscape differences.

    H01: mean <= -sesoi  vs  Ha: mean > -sesoi
    H02: mean >= +sesoi  vs  Ha: mean < +sesoi

    Returns:
        dict with mean, sesoi, p_lower, p_upper, equivalent, lo, hi, verdict.
    """
    if sesoi <= 0:
        raise ValueError(f"sesoi must be positive, got {sesoi}")
    v = np.asarray(diffs, dtype=float).ravel()
    v = v[np.isfinite(v)]
    if v.size < 2:
        raise ValueError(f"need at least two finite differences, got {v.size}")
    p_lower = float(stats.ttest_1samp(v, -sesoi, alternative="greater").pvalue)
    p_upper = float(stats.ttest_1samp(v, +sesoi, alternative="less").pvalue)
    equivalent = bool(p_lower < alpha and p_upper < alpha)
    mean, lo, hi = instance_bootstrap(v, n_boot=n_boot, seed=seed)
    if equivalent:
        verdict = "equivalent"
    elif lo > 0 or hi < 0:
        verdict = "different"
    else:
        verdict = "inconclusive"
    return dict(
        mean=float(mean), sesoi=float(sesoi), n=int(v.size),
        p_lower=p_lower, p_upper=p_upper, equivalent=equivalent,
        lo=float(lo), hi=float(hi), verdict=verdict,
    )


def wilcoxon_mde(
    sigma: float,
    *,
    n: int = 25,
    power: float = 0.80,
    alpha: float = 0.05,
    n_sim: int = 2000,
    seed: int = 0,
) -> float:
    """Smallest |mean| at which two-sided Wilcoxon has ``power`` at this noise.

    ``sigma`` is the SD of the n paired landscape differences. Binary-search
    the effect size. Monte Carlo; pin ``seed``.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    rng = np.random.default_rng(seed)
    mean_w = n * (n + 1) / 4.0
    sd_w = np.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)

    def _power(delta: float) -> float:
        d = rng.normal(delta, sigma, size=(n_sim, n))
        absd = np.abs(d)
        order = np.argsort(absd, axis=1)
        ranks = np.empty_like(absd)
        ranks[np.arange(n_sim)[:, None], order] = np.arange(1, n + 1, dtype=float)
        w = np.where(d > 0, ranks, 0.0).sum(axis=1)
        z = (w - mean_w) / sd_w
        p = 2.0 * stats.norm.sf(np.abs(z))
        return float(np.mean(p < alpha))

    lo, hi = 0.0, max(6.0 * sigma, 1e-3)
    while _power(hi) < power:
        hi *= 2.0
        if hi > 50.0 * sigma:
            return float(hi)
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        if _power(mid) >= power:
            hi = mid
        else:
            lo = mid
    return float(hi)
