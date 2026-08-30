"""Multi-round SPADE: spend the same wells across more adaptive rounds.

**Why this exists, measured rather than assumed.** `docs/SPADE-ROUND-MATCHED-SPEC.md`
holds the well budget fixed at 48 and varies only the round count. Result: `qlognei` at
**ten** rounds certifies 29.0% of the time at LB 0.9063; the *same acquisition* at **two**
rounds certifies **0.0%** -- identical to SPADE, to `lhs`, to everything else at two
rounds. **The margin KX attributed to Bayesian optimisation's design was its round count.**

Adaptivity, not acquisition, is what buys a certificate. This module is the consequence:
it generalises the fixed 40+8 two-plate design to an arbitrary schedule, so the same 48
wells can be spent across 3, 4 or 6 rounds.

**CORRECTED 2026-08-30 — the previous description of this module was false.** It claimed
"the acquisition is the certificate contour, not Bryan's straddle". **Measured false.**

`certificate_straddle` is `1.96*sd - |mean - z_rho*sd - theta|`. Whenever `theta` exceeds
`mean - z_rho*sd` for **every** candidate -- which held for every family at the opening
round, 0.0% of candidates above -- the absolute value resolves and the score collapses to

    (1.96 - z_rho) * sd + mean - theta

so **`theta` is a constant offset and drops out of the ranking entirely.** Rank correlation
between scores at two very different thetas: **exactly 1.000000**, identical argmax
(`docs/SPADE-ACKLEY-THETA-SPEC.md` sec 8).

**What this module actually does, in that regime: a UCB with exploration weight
`1.96 - z_rho`** -- 0.315 at rho=0.95, 1.96 at rho=0.50. `rho` sets exploration; `theta`
does nothing. That also reinterprets LA's measured gap (median regret 0.2996 vs 0.4008)
as an **rho** effect, not evidence that the target contour was moved.

**Two consequences.** The registered KF-3 result -- targeted plate-2 does not beat random
placement -- tested a mechanism that was **never active**. And `theta` was pointed at the
wrong number regardless: the certificate is about `{f >= tau}`, but `theta` was
`tau_frac * mu_max` = 0.80, against tau = 0.0587 on ackley and 0.0774 on hartmann6 at
p=0.30. Pass `theta=tau` to target the region actually being certified.

**Honest limit.** More rounds is not free in a cell-manufacturing lab: a round is a full
differentiation cycle, days to weeks with a fresh cell lot. This module makes the
rounds-vs-wells trade measurable; it does not make rounds cheap.
"""
from __future__ import annotations

import torch


def round_schedule(budget: int, rounds: int, n_init: int) -> tuple[int, list[int]]:
    """Split ``budget`` wells into an opening design plus ``rounds - 1`` adaptive batches.

    Args:
        budget: total wells.
        rounds: total rounds INCLUDING the opening. Must be >= 2.
        n_init: size of the opening space-filling design.

    Returns:
        ``(n_init, batches)`` with ``n_init + sum(batches) == budget`` exactly.

    The remainder is spread one well at a time over the EARLIEST batches rather than
    dumped on the last. Earlier wells inform more subsequent decisions, so a leftover
    well is worth more early -- and dropping it, which an even split would silently do,
    would mean the arm did not spend its budget and is not comparable to one that did.
    """
    budget, rounds, n_init = int(budget), int(rounds), int(n_init)
    if rounds < 2:
        raise ValueError(f"rounds must be >= 2 (1 round is a static design); got {rounds}")
    remaining = budget - n_init
    n_batches = rounds - 1
    if remaining < n_batches:
        raise ValueError(
            f"budget {budget} with n_init {n_init} leaves {remaining} wells for "
            f"{n_batches} adaptive rounds; every round needs at least one well")
    base, extra = divmod(remaining, n_batches)
    batches = [base + (1 if i < extra else 0) for i in range(n_batches)]
    return n_init, batches


def resolve_theta(mu_max, Y, tau_frac: float, theta=None) -> float:
    """The design threshold for one round.

    ``theta`` explicit -> used verbatim. **This is how you target the certification
    threshold**: pass ``theta=tau``. The acquisition targeted ``tau_frac * mu_max`` = 0.80
    while the certificate was computed for ``{f >= tau}``; at p=0.30 that is 0.0587 on
    ackley (13.6x too high) and 0.0774 on hartmann6 (10.3x). ``tau`` is not oracle
    knowledge -- it is the practitioner's own specification ("CD31+ >= 33.2%").

    ``mu_max`` explicit -> ``tau_frac * mu_max``, the committed behaviour, unchanged.

    ``mu_max=None`` -> ``tau_frac`` of the **observed incumbent**, recomputed each round.

    **Why this option exists.** Every runner passed
    ``mu_max = float(getattr(orc, "mu_max", 1.0))`` and **no evaluator defines
    ``mu_max``**, so the fallback made ``theta = 0.80`` on every family. ackley's true
    maximum is 0.4102, so SPADE was straddling a contour **above the global maximum** --
    a level set with no points in it. hartmann6, hill, levy and rosenbrock all top out
    near 1.0, so they never exposed it. ackley is SPADE's only regret loss
    (+0.0652, CI [+0.0203, +0.1104], p=0.004).

    Uses observations only -- it is the EI incumbent, not oracle knowledge.
    """
    if theta is not None:
        return float(theta)
    if mu_max is not None:
        return float(tau_frac) * float(mu_max)
    return float(tau_frac) * float(Y.max())


def multiround_design(orc, dim: int, seed: int, mu_max: float, n_init: int,
                      batches: list[int], rho: float = 0.95,
                      tau_frac: float = 0.80, theta=None):
    """Run one multi-round SPADE campaign and return ``(X, Y, Yvar)``.

    Args:
        orc: oracle exposing ``evaluate(X) -> (Y, Yvar)``.
        dim: design dimension.
        seed: seeds the opening design and every candidate grid.
        mu_max: scale used to place the design threshold. ``None`` selects it from the
            observed incumbent each round -- see :func:`resolve_theta`.
        n_init: opening LHS size.
        batches: adaptive batch sizes, one per subsequent round.
        rho: certificate contour targeted. 0.95 matches `run_versionb.CERT_RHO`.
        tau_frac: design threshold as a fraction of ``mu_max``.

    The model is refitted after **every** batch, which is the entire point: round `k`'s
    proposals must depend on rounds `1..k-1`'s measurements. The candidate grid is
    re-seeded per round so successive batches do not re-propose the same points.
    """
    from boec.certstraddle import batch_lse_rho
    from boec.designspace import gp_adapter
    from boec.lse import exclusion_radius
    from boec.norms import sobol_grid
    from boec.replay import unit_bounds
    from boec.runner import static_design
    from boec.surrogate import build_gp

    bounds = unit_bounds(dim)
    X = static_design(bounds, "lhs", int(n_init), seed)
    Y, Yvar = orc.evaluate(X)

    for k, q in enumerate(batches):
        # Recomputed per round. With an explicit mu_max this is loop-invariant and
        # identical to the committed behaviour; with mu_max=None it tracks the incumbent.
        theta_k = resolve_theta(mu_max, Y, tau_frac, theta)
        model = build_gp(X, Y, Yvar, bounds)
        ad = gp_adapter(model)
        # Re-seed per round: a fixed grid would offer the same candidates every time and
        # the exclusion radius alone would then drive the batch, not the data.
        cand = sobol_grid(dim, 2000, seed=seed * 131 + k)
        Xq = batch_lse_rho(ad, cand, theta_k, int(q),
                           exclude=exclusion_radius(model), rho=float(rho))
        Yq, Vq = orc.evaluate(Xq)
        X = torch.cat([X, Xq])
        Y = torch.cat([Y, Yq])
        Yvar = torch.cat([Yvar, Vq])
        del model, cand
    return X, Y, Yvar
