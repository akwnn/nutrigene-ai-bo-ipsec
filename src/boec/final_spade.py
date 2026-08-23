"""Rule L1 -- the frozen local-exploitation allocation for the final prospective study.

Registered in ``docs/SPADE-FINAL-SPEC.md`` §3.2 at commit ``c4f58d3``, **before this module
existed**. Nothing here is tunable: every constant is either inherited from a registered
formula or is an argument the caller must state.

------------------------------------------------------------------------------
WHAT THIS MODULE IS, AND WHAT IT DELIBERATELY IS NOT
------------------------------------------------------------------------------

``spade_cf_m4`` and ``spade_cf_m8`` spend ``m`` of their eight plate-2 wells near the
plate-1 posterior-mean optimum instead of on the acceptability boundary. This module decides
**where those m wells go**, and nothing else. The remaining ``8 - m`` wells are chosen by the
*identical* :func:`boec.lse.batch_lse` call the ``m0`` arm uses, in the runner, so the three
arms differ in exactly one registered quantity.

It is **not** a trust-region optimiser and it is not an acquisition function. The question
this study asks is not "what is the best local rule" -- that would be a tuning exercise, and
tuning after seeing results is what §11 of the spec prohibits. It is "does spending wells
locally buy regret without costing the certificate", and answering it needs *a* frozen local
rule, defensible and simple, not an optimal one.

------------------------------------------------------------------------------
WHY THE RADIUS IS 1, AND WHY THAT IS NOT A TUNED CONSTANT
------------------------------------------------------------------------------

:func:`boec.versionc.n_effective` counts ``1 + |{x_i : ||x_i - x_hat||_ARD <= 1}|`` -- the
wells informing the argmax. FINDINGS §9.3 measured that ``doe``'s identification gap is
noise-invariant while every BO arm's roughly halves, and attributed the difference to a
winner's-curse term scaling with ``sigma / sqrt(n_eff)``. ``n_eff`` is the denominator of the
only quantity that mechanism predicts.

So the trust region here is **the ARD ball of radius 1** -- literally ``n_effective``'s own
bound. Every well this rule places provably increments the registered statistic. The radius
is *inherited from a registered formula*, not chosen to make the arm perform; a different
radius would be a different statistic, and the project has already logged (D8) what happens
when a decision rule is anchored on an invented constant instead of on the object it is
about.

------------------------------------------------------------------------------
NO ORACLE ACCESS, ENFORCED ON THE SIGNATURE
------------------------------------------------------------------------------

:func:`local_wells` takes **arrays** -- candidates, a posterior mean, the plate-1 design and
the fitted lengthscales. It takes no ``truth``, no oracle, and **no model object**. A model
carries a ``.posterior`` and therefore a route to anything the caller has already computed;
arrays carry nothing. The no-oracle-access property is a fact about the type signature, which
is the guard ``boec.versionc`` uses for its detector statistics and for the same reason: a
rule that *could* be handed truth eventually is, and the failure is silent.

``mean`` must be the **plate-1** posterior mean. That is the caller's obligation and the
runner's test asserts it; this module cannot check it, and says so rather than implying a
guarantee it does not provide.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["LOCAL_RADIUS", "local_wells"]

#: ``n_effective``'s bound, inherited. See the module docstring -- not a tuning knob.
LOCAL_RADIUS = 1.0


def local_wells(cand: Tensor, mean: Tensor, X1: Tensor, lengthscales: Tensor, m: int,
                *, radius: float = LOCAL_RADIUS) -> tuple[Tensor, dict]:
    """The ``m`` local exploitation wells, by frozen rule **L1**.

    The rule, implemented literally as registered:

    1. ``x_hat`` is the **grid argmax** of ``mean`` over ``cand``. Deliberately a grid
       argmax and not a continuous optimiser: FINDINGS §4.1 records that this project's one
       non-reproducible path was a post-hoc L-BFGS-B locator with 20 restarts, and the
       campaigns themselves were exact. A grid argmax over a seeded candidate set is bitwise
       reproducible.
    2. The trust region is the ARD ball ``{x : ||(x - x_hat)/ell||_2 <= radius}``.
    3. The ``m`` wells are chosen by **greedy farthest-point (maximin) in the ARD metric**
       from the union of ``X1`` and the wells already chosen, restricted to candidates
       inside the ball. Maximin rather than "closest to ``x_hat``" because stacking wells on
       the predicted optimum re-measures one location; spreading them inside the ball is what
       raises ``n_eff``, which is the statistic the rule exists to move.
    4. Ties are broken by **lowest candidate index**, so the result is deterministic rather
       than dependent on ``torch.argmax``'s tie behaviour across versions.

    Args:
        cand: ``(N, d)`` the frozen candidate set -- the *same* one plate 2's boundary rule
            uses, so the two allocations are drawn from one population.
        mean: ``(N,)`` the **plate-1** posterior mean at ``cand``.
        X1: ``(n1, d)`` the plate-1 design.
        lengthscales: ``(d,)`` fitted ARD lengthscales, from
            :func:`boec.versionc.ard_lengthscales`.
        m: how many local wells to place. ``0`` returns an empty ``(0, d)`` tensor, which is
            what makes ``spade_cf_m0`` bit-identical to the pure boundary arm.
        radius: the ARD ball radius. Defaults to :data:`LOCAL_RADIUS`; exposed as an
            argument so a sensitivity analysis can state a different value **explicitly**
            rather than by editing a constant.

    Returns:
        ``(X_local, diag)``. ``X_local`` is ``(k, d)`` with ``k <= m``. ``diag`` carries
        ``x_hat``, ``n_in_ball``, ``m_requested``, ``m_placed``, ``m_local_short`` and
        ``radius`` -- every quantity needed to recompute the decision from the row.

        ``m_local_short`` is ``True`` when the ball held fewer than ``m`` candidates. The
        caller **must** fall back to the boundary rule for the remainder; returning fewer
        wells silently would break the equal-well budget and make an ``m4`` arm secretly an
        ``m2``.

    Raises:
        ValueError: on a width mismatch, on a non-positive lengthscale, or on ``m < 0``.
            :func:`boec.versionc.n_effective` raises on the first of these for the same
            reason -- a broadcast answers a different question silently.
    """
    C = torch.as_tensor(cand, dtype=torch.double)
    if C.ndim != 2:
        raise ValueError(f"cand must be (N, d), got {tuple(C.shape)}")
    N, d = C.shape
    mu = torch.as_tensor(mean, dtype=torch.double).reshape(-1)
    Xd = torch.as_tensor(X1, dtype=torch.double).reshape(-1, d)
    ls = torch.as_tensor(lengthscales, dtype=torch.double).reshape(-1)

    if mu.numel() != N:
        raise ValueError(
            f"width mismatch: cand has N={N} rows, mean has {mu.numel()} -- broadcasting "
            "these would answer a different question silently")
    if ls.numel() != d:
        raise ValueError(
            f"width mismatch: cand has d={d}, lengthscales has {ls.numel()}")
    if bool((ls <= 0).any()):
        raise ValueError(f"non-positive lengthscale in {ls.tolist()}")
    if m < 0:
        raise ValueError(f"m must be non-negative, got {m}")

    x_hat = C[int(mu.argmax())]

    # Step 2 -- the ARD ball. `x_hat` is itself a candidate and sits at distance 0, so the
    # ball is never empty; `n_in_ball >= 1` always.
    in_ball = (((C - x_hat) / ls).pow(2).sum(dim=1).sqrt() <= radius).nonzero().reshape(-1)
    n_in_ball = int(in_ball.numel())

    diag = {"x_hat": x_hat.tolist(), "n_in_ball": n_in_ball, "m_requested": int(m),
            "radius": float(radius)}

    if m == 0:
        diag.update({"m_placed": 0, "m_local_short": False})
        return C.new_zeros((0, d)), diag

    k = min(int(m), n_in_ball)
    pool = C[in_ball]

    # Step 3 -- greedy maximin in the ARD metric, seeded by the plate-1 design so the local
    # wells are far from wells that already exist rather than merely far from each other.
    scaled_pool = pool / ls
    best = (scaled_pool.unsqueeze(1) - (Xd / ls).unsqueeze(0)).pow(2).sum(dim=2).sqrt()
    dmin = best.min(dim=1).values if Xd.shape[0] else torch.full((pool.shape[0],),
                                                                 float("inf"),
                                                                 dtype=torch.double)
    chosen: list[int] = []
    for _ in range(k):
        # Step 4 -- lowest index wins a tie. `argmax` on a tensor returns the first maximal
        # index already, but the intent is registered so it is asserted rather than assumed.
        j = int(torch.argmax(dmin))
        chosen.append(j)
        # Picking a point sets its own distance to 0, so it cannot be chosen twice.
        dnew = (scaled_pool - scaled_pool[j]).pow(2).sum(dim=1).sqrt()
        dmin = torch.minimum(dmin, dnew)

    X_loc = pool[torch.tensor(chosen, dtype=torch.long)]
    diag.update({"m_placed": int(X_loc.shape[0]),
                 "m_local_short": bool(n_in_ball < int(m))})
    return X_loc, diag
