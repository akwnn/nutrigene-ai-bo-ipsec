"""Q37 / T2.2 — the replay's "NOT SUPPORTED" is a power statement, not a failed claim.

    python scripts/run_q37_replay_power.py     # log at results/q37-replay-power.log

**Reads nothing from and writes nothing to the registered replay artefacts.** It
re-derives the per-seed first-hit vectors by importing `run_replay_hall_ogle` and
calling its own functions, so the numbers are that run's numbers, not a re-implementation.
`results/replay-hall-ogle.log` is left exactly as it was.

WHY
---
Q31 registered "BO reaches a top-5 condition in fewer evaluations than the published
design" and the replay reported NULL at both stages. Written up as "NOT SUPPORTED" that
reads like a claim that was tested and lost. It is mostly a claim that could not be
tested at the achieved sample size and menu geometry, and saying so is both more honest
and more useful than the bare verdict.

Two quantities make the point, and neither of them requires re-running anything:

1. **Minimum detectable effect.** How large a head start would BO have needed for this
   design to detect it at 80% power? Computed by simulation on the observed paired
   differences rather than from a normal approximation, because the endpoint is a small
   censored integer (1..BUDGET+1) and a t-based MDE would be wrong about its tails.

2. **The structural ceiling.** With N candidates on the menu, K of them in the target
   set, and only BUDGET - N_INIT adaptive evaluations, there is a floor on how fast ANY
   method can be, and a uniform draw is already close to it. Confining BO to a fixed
   menu of 23-25 items removes the capability under test: it cannot propose a condition
   the published design did not run.

The exact first-hit distribution under uniform sampling without replacement is
    P(T > m) = C(N-K, m) / C(N, m)
so the whole comparator distribution is available in closed form, with no simulation.
"""

from __future__ import annotations

import json
import os
import sys
from math import comb
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import warnings

import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import torch                                            # noqa: E402
from scipy.stats import wilcoxon                        # noqa: E402

import run_replay_hall_ogle as rp                       # noqa: E402

N_BOOT = 4000
POWER_TARGET = 0.80
ALPHA = 0.05
RULE = "=" * 88


def per_seed_hits(stage: str) -> dict:
    """Re-derive the replay's per-seed vectors using the replay's own functions."""
    X, y, sd, ids = rp.load(stage)
    valid = np.where(~np.isnan(y))[0]
    top = set(valid[np.argsort(y[valid])[::-1][: rp.K]].tolist())
    d = X.shape[1]
    bounds = torch.stack([torch.full((d,), -1.0, dtype=torch.double),
                          torch.full((d,), 1.0, dtype=torch.double)])

    bo_hits, rd_hits = [], []
    for seed in range(rp.N_SEEDS):
        rng = np.random.default_rng(seed)
        opening = rng.choice(valid, size=rp.N_INIT, replace=False).tolist()
        ev = rp.LookupEvaluator(X, y, sd, rp.METRIC)
        bo_order, _ = rp.run_bo(ev, valid, X, opening, bounds, seed)
        rest = [i for i in valid.tolist() if i not in opening]
        rd_order = opening + rng.permutation(rest).tolist()[: rp.BUDGET - rp.N_INIT]
        bo_hits.append(rp.evals_to_first_hit(bo_order, top))
        rd_hits.append(rp.evals_to_first_hit(rd_order, top))
    return dict(stage=stage, n_candidates=len(valid), n_total=len(y),
                bo=np.array(bo_hits, float), rd=np.array(rd_hits, float))


def mde(diff: np.ndarray, *, n_boot: int = N_BOOT) -> float:
    """Smallest true effect this design detects at 80% power, by simulation.

    **The effect must be injected DISCRETELY.** The endpoint is "which evaluation
    first hit a top-k condition" — a censored integer on 1..BUDGET+1. A real advantage
    for BO means it arrives one evaluation sooner on some FRACTION of seeds; there is
    no such thing as arriving 0.1 evaluations sooner. So a candidate effect of size `q`
    is injected as `+1` on a Bernoulli(q) subset of resampled seeds, which has mean
    effect `q` while remaining a difference of integers.

    **And the null must be imposed by SIGN-FLIPPING, not by subtracting the mean.**
    The signed-rank null is symmetry about zero, and sign-flipping imposes it while
    preserving both the magnitudes and — critically — the exact ties. Most seeds here
    have a difference of exactly 0, because 63% of the time a top-k condition is already
    in the 4-point opening the two arms share.

    Two wrong versions of this function are recorded rather than quietly replaced,
    because both made the design look POWERFUL, which is the opposite of the finding:

      1. A continuous shift `+delta` applied to every seed. Not achievable on an integer
         endpoint, and it turns a near-all-zero vector uniformly positive.
      2. Centring by `diff - diff.mean()`. At stage 2 the mean is -0.025, so every exact
         tie became +0.025 and every difference became positive — Wilcoxon then rejects
         at any injected effect, giving an absurd MDE of 0.03 evaluations against a
         reported CI of [-0.50, +0.40].

    Simulation rather than `(z_a + z_b) * se / sqrt(n)` for the same discreteness reason:
    the endpoint is bounded and skewed, and a normal approximation misstates exactly the
    tail a power calculation lives in.
    """
    n = len(diff)
    rng = np.random.default_rng(0)
    trials = max(n_boot // 8, 200)
    for q in np.arange(0.025, 2.0001, 0.025):
        rejects = 0
        for _ in range(trials):
            base = diff[rng.integers(0, n, n)]
            base = base * rng.choice([-1.0, 1.0], size=n)      # symmetry about zero
            s = base + (rng.random(n) < q).astype(float)       # discrete injected effect
            try:
                if wilcoxon(s).pvalue < ALPHA:
                    rejects += 1
            except ValueError:            # all-zero vector: no evidence, not a rejection
                continue
        if rejects / trials >= POWER_TARGET:
            return float(q)               # mean effect, in evaluations
    return float("nan")


def uniform_first_hit(N: int, K: int, budget: int) -> dict:
    """Exact distribution of evaluations-to-first-hit for a uniform draw, no simulation.

    `P(T > m) = C(N-K, m) / C(N, m)` — the chance the first m draws all miss.
    """
    surv = [comb(N - K, m) / comb(N, m) if m <= N - K else 0.0 for m in range(budget + 1)]
    pmf = [surv[m - 1] - surv[m] for m in range(1, budget + 1)]
    p_never = surv[budget]
    mean_capped = sum(m * p for m, p in zip(range(1, budget + 1), pmf)) + \
        (budget + 1) * p_never
    cum, median = 0.0, None
    for m, p in zip(range(1, budget + 1), pmf):
        cum += p
        if median is None and cum >= 0.5:
            median = m
    return dict(median=median, mean_capped=mean_capped, p_never=p_never,
                p_hit_in_opening=1.0 - surv[min(rp.N_INIT, len(surv) - 1)])


def report(h: dict) -> dict:
    stage, bo, rd = h["stage"], h["bo"], h["rd"]
    N, K, B, n_init = h["n_candidates"], rp.K, rp.BUDGET, rp.N_INIT
    diff = rd - bo                      # >0 means BO got there sooner
    obs = float(diff.mean())
    m = mde(diff)
    u = uniform_first_hit(N, K, B)

    print(f"\n{RULE}\nQ37 · {stage} · N={N} candidates · K={K} targets · "
          f"budget={B} ({n_init} opening + {B - n_init} adaptive) · n={len(bo)} seeds\n{RULE}")
    print(f"  observed effect (random − BO)      {obs:+.4f} evaluations")
    print(f"  MINIMUM DETECTABLE EFFECT          {m:.2f} evaluations "
          f"at {int(POWER_TARGET * 100)}% power, alpha={ALPHA}")
    print(f"  => the experiment BOUNDS the effect below {m:.2f} evaluations.")
    print(f"     It does not show the effect is zero; it shows the design could not "
          f"have\n     seen anything smaller than that.")

    print(f"\n  the structural ceiling — a uniform draw from this menu:")
    print(f"    median evals to first top-{K}     {u['median']}   "
          f"(observed: BO {np.median(bo):.1f}, random {np.median(rd):.1f})")
    print(f"    mean, censored at budget+1        {u['mean_capped']:.3f}")
    print(f"    P(a top-{K} is already in the {n_init}-point opening) = "
          f"{u['p_hit_in_opening']:.3f}")
    print(f"    P(never found in {B})              {u['p_never']:.3f}")
    print(f"    {100 * K / N:.0f}% of the menu is in the target set, and only "
          f"{B - n_init} of {B} evaluations are adaptive.")
    if u["p_hit_in_opening"] > 0.5:
        print(f"    *** More than half the time the target is already in the SHARED "
              f"opening,\n        before either method has proposed anything. Those "
              f"seeds carry no signal\n        about the methods at all.")
    return dict(stage=stage, n=len(bo), observed=obs, mde=m,
                uniform=u, n_candidates=N, budget=B, n_init=n_init)


def main() -> None:
    out = []
    for stage in ("stage2", "stage1"):
        out.append(report(per_seed_hits(stage)))
    print(f"\n{RULE}\nHOW THIS SHOULD BE WRITTEN UP\n{RULE}")
    for o in out:
        print(f"  {o['stage']}: \"the head start is bounded below "
              f"{o['mde']:.1f} evaluations at 80% power\"  —  NOT \"BO is no faster\".")
    print("\n  And the structural reason belongs in the same breath: a fixed menu of\n"
          "  23-25 conditions with a fifth of it in the target set, at a budget of 8 of\n"
          "  which 4 are a shared opening, cannot separate any two methods. Confining BO\n"
          "  to the published design's own conditions also removes the capability under\n"
          "  test -- it cannot propose a condition the published study never ran.")
    (ROOT / "results" / "q37-replay-power.json").write_text(json.dumps(out, indent=1))
    print(f"\n  written to results/q37-replay-power.json")


if __name__ == "__main__":
    main()
